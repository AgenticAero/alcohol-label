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
