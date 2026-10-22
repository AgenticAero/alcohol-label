"""Shared identifiers and states for verification data contracts.

Processing failures (timeouts, invalid provider responses) are deliberately not
members of any enum here; they belong to a separate error contract.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class FieldId(StrEnum):
    """Application fields and raw label text that can be extracted and compared."""

    BRAND = "brand"
    CLASS_TYPE = "class_type"
    ALCOHOL_CONTENT = "alcohol_content"
    NET_CONTENTS = "net_contents"
    PRODUCER_NAME = "producer_name"
    PRODUCER_ADDRESS = "producer_address"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    WARNING_TEXT = "warning_text"


class CheckId(StrEnum):
    """Individual verification checks; each yields one CheckOutcome."""

    BRAND = "brand"
    CLASS_TYPE = "class_type"
    ALCOHOL_CONTENT = "alcohol_content"
    NET_CONTENTS = "net_contents"
    PRODUCER_NAME = "producer_name"
    PRODUCER_ADDRESS = "producer_address"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    WARNING_WORDING = "warning_wording"
    WARNING_HEADING_CASE = "warning_heading_case"
    WARNING_HEADING_BOLD = "warning_heading_bold"
    WARNING_BODY_NOT_BOLD = "warning_body_not_bold"


class CheckOutcome(StrEnum):
    """Result of evaluating one check."""

    MATCH = "match"
    DISCREPANCY = "discrepancy"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUATED = "not_evaluated"


class ExtractionState(StrEnum):
    """What extraction found for one field in the supplied images."""

    OBSERVED = "observed"
    MISSING = "missing"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"


class BeverageCategory(StrEnum):
    """Beverage categories; the prototype supports distilled spirits only."""

    DISTILLED_SPIRITS = "distilled_spirits"


class Unit(StrEnum):
    """Explicit units for application measurements."""

    PERCENT_ABV = "percent_abv"
    MILLILITER = "ml"
    LITER = "l"
    FLUID_OUNCE = "fl_oz"


_VOLUME_UNITS = frozenset({Unit.MILLILITER, Unit.LITER, Unit.FLUID_OUNCE})


@dataclass(frozen=True, slots=True)
class Measurement:
    """A positive decimal quantity with an explicit unit."""

    value: Decimal
    unit: Unit

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ValueError("measurement value must be a finite Decimal")
        if self.value <= 0:
            raise ValueError("measurement value must be positive")


@dataclass(frozen=True, slots=True)
class ImageReference:
    """Reference to one supplied label image; holds no image content."""

    image_id: str
    uri: str

    def __post_init__(self) -> None:
        if not self.image_id.strip() or not self.uri.strip():
            raise ValueError("image_id and uri must not be blank")


@dataclass(frozen=True, slots=True)
class ApplicationData:
    """Application claims for one review, independent of image extraction.

    Expected values default to ``None`` meaning "not supplied"; no defaults are
    invented. Structural problems raise ``ValueError``. Missing required inputs
    are reported by ``missing_required_fields`` so they can be surfaced as
    unresolved checks rather than crashes. The warning statement is not an
    application input; its canonical text is pinned in code.
    """

    application_id: str
    beverage_category: BeverageCategory
    is_imported: bool
    images: tuple[ImageReference, ...]
    brand: str | None = None
    class_type: str | None = None
    alcohol_content: Measurement | None = None
    net_contents: Measurement | None = None
    producer_name: str | None = None
    producer_address: str | None = None
    country_of_origin: str | None = None

    def __post_init__(self) -> None:
        if not self.application_id.strip():
            raise ValueError("application_id must not be blank")
        if not 1 <= len(self.images) <= 2:
            raise ValueError("one or two image references are required")
        if len({image.image_id for image in self.images}) != len(self.images):
            raise ValueError("image ids must be unique within an application")
        for field_id in (
            FieldId.BRAND,
            FieldId.CLASS_TYPE,
            FieldId.PRODUCER_NAME,
            FieldId.PRODUCER_ADDRESS,
            FieldId.COUNTRY_OF_ORIGIN,
        ):
            text = getattr(self, field_id.value)
            if text is not None and not text.strip():
                raise ValueError(f"{field_id.value} must be None or non-blank text")
        if (
            self.alcohol_content is not None
            and self.alcohol_content.unit is not Unit.PERCENT_ABV
        ):
            raise ValueError("alcohol_content must use percent_abv")
        if (
            self.net_contents is not None
            and self.net_contents.unit not in _VOLUME_UNITS
        ):
            raise ValueError("net_contents must use a volume unit")

    def missing_required_fields(self) -> tuple[FieldId, ...]:
        """Required expected values not supplied; country is required for imports."""
        required = [
            FieldId.BRAND,
            FieldId.CLASS_TYPE,
            FieldId.ALCOHOL_CONTENT,
            FieldId.NET_CONTENTS,
            FieldId.PRODUCER_NAME,
            FieldId.PRODUCER_ADDRESS,
        ]
        if self.is_imported:
            required.append(FieldId.COUNTRY_OF_ORIGIN)
        return tuple(f for f in required if getattr(self, f.value) is None)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Region of an image as fractions of its width and height (0 to 1)."""

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        coords = (self.left, self.top, self.right, self.bottom)
        if not all(0 <= c <= 1 for c in coords):
            raise ValueError("bounding box coordinates must be within 0 and 1")
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("bounding box must have positive width and height")


@dataclass(frozen=True, slots=True)
class EvidenceLocation:
    """Where on an image an observation was found; a box, a crop, or both."""

    box: BoundingBox | None = None
    crop_ref: str | None = None

    def __post_init__(self) -> None:
        if self.crop_ref is not None and not self.crop_ref.strip():
            raise ValueError("crop_ref must be None or non-blank")
        if self.box is None and self.crop_ref is None:
            raise ValueError("location needs a bounding box or crop_ref")


@dataclass(frozen=True, slots=True)
class Observation:
    """One candidate reading from one image.

    ``raw_text`` is kept verbatim (case, punctuation, whitespace); it is never
    normalized. ``parsed_value`` is a separate, optional interpretation.
    ``image_id`` matches ``ImageReference.image_id`` and implies no front/back.
    """

    raw_text: str
    image_id: str
    parsed_value: str | Decimal | Measurement | None = None
    location: EvidenceLocation | None = None

    def __post_init__(self) -> None:
        if not self.raw_text:
            raise ValueError("raw_text must not be empty")
        if not self.image_id.strip():
            raise ValueError("image_id must not be blank")
        if self.parsed_value is not None and not isinstance(
            self.parsed_value, (str, Decimal, Measurement)
        ):
            raise ValueError("parsed_value must be str, Decimal, Measurement, or None")


@dataclass(frozen=True, slots=True)
class ExtractedField:
    """What extraction found for one field, independent of expected values.

    Conflicting observations are all kept; none is selected. Unknowns use an
    explicit state with no observations (or only uncertain candidates) and an
    explanation. No confidence score is carried.
    """

    field_id: FieldId
    state: ExtractionState
    observations: tuple[Observation, ...] = ()
    explanation: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        if not isinstance(self.state, ExtractionState):
            raise TypeError("state must be an ExtractionState")
        count = len(self.observations)
        if self.state is ExtractionState.OBSERVED and count != 1:
            raise ValueError("observed requires exactly one observation")
        if self.state is ExtractionState.MISSING and count != 0:
            raise ValueError("missing must have no observations")
        if self.state is ExtractionState.CONFLICTING and (
            count < 2 or len({o.raw_text for o in self.observations}) < 2
        ):
            raise ValueError("conflicting requires differing observations")
        if self.state is not ExtractionState.OBSERVED and not (
            self.explanation and self.explanation.strip()
        ):
            raise ValueError(f"{self.state.value} requires an explanation")


_CHECK_FIELD: dict[CheckId, FieldId] = {
    CheckId.BRAND: FieldId.BRAND,
    CheckId.CLASS_TYPE: FieldId.CLASS_TYPE,
    CheckId.ALCOHOL_CONTENT: FieldId.ALCOHOL_CONTENT,
    CheckId.NET_CONTENTS: FieldId.NET_CONTENTS,
    CheckId.PRODUCER_NAME: FieldId.PRODUCER_NAME,
    CheckId.PRODUCER_ADDRESS: FieldId.PRODUCER_ADDRESS,
    CheckId.COUNTRY_OF_ORIGIN: FieldId.COUNTRY_OF_ORIGIN,
    CheckId.WARNING_WORDING: FieldId.WARNING_TEXT,
    CheckId.WARNING_HEADING_CASE: FieldId.WARNING_TEXT,
    CheckId.WARNING_HEADING_BOLD: FieldId.WARNING_TEXT,
    CheckId.WARNING_BODY_NOT_BOLD: FieldId.WARNING_TEXT,
}

_WARNING_CHECKS = frozenset(c for c in CheckId if c.value.startswith("warning_"))

_CheckValue = str | Decimal | Measurement | None


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Link to one observation supporting a check.

    Points at ``ExtractedField.observations[observation_index]`` for
    ``field_id``; ``image_id`` names the source image of that observation.
    """

    field_id: FieldId
    observation_index: int
    image_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.field_id, FieldId):
            raise TypeError("field_id must be a FieldId")
        if (
            not isinstance(self.observation_index, int)
            or isinstance(self.observation_index, bool)
            or self.observation_index < 0
        ):
            raise ValueError("observation_index must be a non-negative integer")
        if not self.image_id.strip():
            raise ValueError("image_id must not be blank")


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of one check; records a result, performs no comparison.

    Schema validation enforces structure only. Whether the outcome is the right
    one for the expected and observed values, and whether evidence references
    resolve to real observations and images, belong to comparison logic.
    """

    check_id: CheckId
    outcome: CheckOutcome
    field_id: FieldId | None = None
    expected_value: _CheckValue = None
    observed_value: _CheckValue = None
    explanation: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if not isinstance(self.check_id, CheckId):
            raise TypeError("check_id must be a CheckId")
        if not isinstance(self.outcome, CheckOutcome):
            raise TypeError("outcome must be a CheckOutcome")
        expected_field = _CHECK_FIELD[self.check_id]
        if self.field_id is None:
            if self.check_id not in _WARNING_CHECKS:
                raise ValueError(f"{self.check_id.value} requires a field_id")
        elif self.field_id is not expected_field:
            raise ValueError(
                f"{self.check_id.value} must use field {expected_field.value}"
            )
        for value in (self.expected_value, self.observed_value):
            if value is not None and not isinstance(value, (str, Decimal, Measurement)):
                raise ValueError("values must be str, Decimal, Measurement, or None")
        for ref in self.evidence:
            if not isinstance(ref, EvidenceRef):
                raise TypeError("evidence must contain EvidenceRef items")
            if ref.field_id is not expected_field:
                raise ValueError("evidence must reference the check's field")
        if self.outcome is not CheckOutcome.MATCH and not (
            self.explanation and self.explanation.strip()
        ):
            raise ValueError(f"{self.outcome.value} requires an explanation")
        if self.outcome is CheckOutcome.DISCREPANCY and not self.evidence:
            raise ValueError("discrepancy requires evidence")
