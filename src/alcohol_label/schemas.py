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
        if self.state is ExtractionState.OBSERVED and (
            count < 1
            or len({o.raw_text for o in self.observations}) != 1
            or len({o.image_id for o in self.observations}) != count
        ):
            raise ValueError(
                "observed requires equal readings from distinct source images"
            )
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


class StyleJudgement(StrEnum):
    """Visual weight judgement for one part of the warning in one image."""

    BOLD = "bold"
    NOT_BOLD = "not_bold"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class WarningStyleObservation:
    """Heading and body weight seen in one image; not a transcription field.

    Weight is judged from the image, relative between heading and body. No
    confidence score and no physical type size are carried. An uncertain
    judgement needs a reason so a reviewer knows what to look at.
    """

    image_id: str
    heading: StyleJudgement
    body: StyleJudgement
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.image_id, str) or not self.image_id.strip():
            raise ValueError("image_id must not be blank")
        for judgement in (self.heading, self.body):
            if not isinstance(judgement, StyleJudgement):
                raise TypeError("judgements must be StyleJudgement values")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")
        uncertain = StyleJudgement.UNCERTAIN in (self.heading, self.body)
        if uncertain and not (self.reason and self.reason.strip()):
            raise ValueError("an uncertain judgement requires a reason")


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
        if not isinstance(self.observation_index, int) or isinstance(
            self.observation_index, bool
        ):
            raise TypeError("observation_index must be an integer")
        if self.observation_index < 0:
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


class ProcessingStage(StrEnum):
    """Pipeline stage in which a processing failure occurred."""

    INPUT_VALIDATION = "input_validation"
    IMAGE_DECODING = "image_decoding"
    EXTRACTION = "extraction"
    COMPARISON = "comparison"


class ErrorCode(StrEnum):
    """Stable identifiers for processing failures; never label findings."""

    PROVIDER_TIMEOUT = "provider_timeout"
    ENDPOINT_BLOCKED = "endpoint_blocked"
    RATE_LIMITED = "rate_limited"
    INVALID_PROVIDER_RESPONSE = "invalid_provider_response"
    IMAGE_UNREADABLE = "image_unreadable"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True, slots=True)
class ProcessingError:
    """An execution failure, kept apart from check outcomes.

    ``message`` is user-facing. There is deliberately no diagnostics field:
    provider detail, URLs, stack traces and credentials belong in server-side
    logs. The schema cannot prove a message is safe; its author must ensure it.
    """

    stage: ProcessingStage
    code: ErrorCode
    message: str
    retryable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ProcessingStage):
            raise TypeError("stage must be a ProcessingStage")
        if not isinstance(self.code, ErrorCode):
            raise TypeError("code must be an ErrorCode")
        if not isinstance(self.message, str):
            raise TypeError("message must be a string")
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be a bool")
        if not self.message.strip():
            raise ValueError("message must not be blank")


class ReviewStatus(StrEnum):
    """Whether a review produced a result for every check without failures."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


_CLEAR_OUTCOMES = frozenset({CheckOutcome.MATCH, CheckOutcome.NOT_APPLICABLE})


@dataclass(frozen=True, slots=True)
class ReviewResponse:
    """Check results and processing errors for one application, kept separate.

    Partial check results may accompany processing errors. Status and
    all-clear are derived so they cannot disagree with the data. A later
    ``VerificationResult`` (summary, scope, versions, timings) will wrap or
    extend this record.
    """

    application_id: str
    check_results: tuple[CheckResult, ...] = ()
    processing_errors: tuple[ProcessingError, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_results", tuple(self.check_results))
        object.__setattr__(self, "processing_errors", tuple(self.processing_errors))
        if not isinstance(self.application_id, str):
            raise TypeError("application_id must be a string")
        if not self.application_id.strip():
            raise ValueError("application_id must not be blank")
        for result in self.check_results:
            if not isinstance(result, CheckResult):
                raise TypeError("check_results must contain CheckResult items")
        for error in self.processing_errors:
            if not isinstance(error, ProcessingError):
                raise TypeError("processing_errors must contain ProcessingError items")
        check_ids = [r.check_id for r in self.check_results]
        if len(set(check_ids)) != len(check_ids):
            raise ValueError("each check may have only one result")

    @property
    def status(self) -> ReviewStatus:
        """Complete only without processing errors and with every check present."""
        has_all_checks = {r.check_id for r in self.check_results} == set(CheckId)
        if not self.processing_errors and has_all_checks:
            return ReviewStatus.COMPLETE
        return ReviewStatus.INCOMPLETE

    @property
    def all_clear(self) -> bool:
        """True only for a complete review where every outcome is clear."""
        return self.status is ReviewStatus.COMPLETE and all(
            r.outcome in _CLEAR_OUTCOMES for r in self.check_results
        )


# JSON-compatible serialization. Decimals are strings and enums are their
# values. Typed values are tagged so str, Decimal and Measurement survive a
# round trip. Malformed input raises ValueError (or TypeError from the models).


def _value_to_json(value: str | Decimal | Measurement | None) -> object:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    return {"measurement": {"value": str(value.value), "unit": value.unit.value}}


def _decimal_from_json(text: object) -> Decimal:
    if not isinstance(text, str):
        raise TypeError("decimal values must be serialized as strings")
    try:
        return Decimal(text)
    except ArithmeticError as error:
        raise ValueError("invalid decimal value") from error


def _value_from_json(data: object) -> str | Decimal | Measurement | None:
    if data is None or isinstance(data, str):
        return data
    if isinstance(data, dict) and set(data) == {"decimal"}:
        return _decimal_from_json(data["decimal"])
    if isinstance(data, dict) and set(data) == {"measurement"}:
        m = data["measurement"]
        return Measurement(_decimal_from_json(m["value"]), Unit(m["unit"]))
    raise ValueError("unrecognized typed value")


def _guard(build, data: object, name: str):
    if not isinstance(data, dict):
        raise TypeError(f"{name} must be an object")
    try:
        return build(data)
    except KeyError as error:
        raise ValueError(f"{name} is missing {error.args[0]!r}") from error


def application_to_dict(app: ApplicationData) -> dict:
    return {
        "application_id": app.application_id,
        "beverage_category": app.beverage_category.value,
        "is_imported": app.is_imported,
        "images": [{"image_id": i.image_id, "uri": i.uri} for i in app.images],
        "brand": app.brand,
        "class_type": app.class_type,
        "alcohol_content": _value_to_json(app.alcohol_content),
        "net_contents": _value_to_json(app.net_contents),
        "producer_name": app.producer_name,
        "producer_address": app.producer_address,
        "country_of_origin": app.country_of_origin,
    }


def application_from_dict(data: dict) -> ApplicationData:
    def build(d: dict) -> ApplicationData:
        measures = {}
        for key in ("alcohol_content", "net_contents"):
            value = _value_from_json(d.get(key))
            if value is not None and not isinstance(value, Measurement):
                raise ValueError(f"{key} must be a measurement")
            measures[key] = value
        return ApplicationData(
            application_id=d["application_id"],
            beverage_category=BeverageCategory(d["beverage_category"]),
            is_imported=d["is_imported"],
            images=tuple(ImageReference(i["image_id"], i["uri"]) for i in d["images"]),
            brand=d.get("brand"),
            class_type=d.get("class_type"),
            producer_name=d.get("producer_name"),
            producer_address=d.get("producer_address"),
            country_of_origin=d.get("country_of_origin"),
            **measures,
        )

    return _guard(build, data, "application")


def _location_to_json(location: EvidenceLocation | None) -> dict | None:
    if location is None:
        return None
    box = location.box
    box_data = (
        None
        if box is None
        else {
            "left": box.left,
            "top": box.top,
            "right": box.right,
            "bottom": box.bottom,
        }
    )
    return {"box": box_data, "crop_ref": location.crop_ref}


def _location_from_json(data: dict | None) -> EvidenceLocation | None:
    if data is None:
        return None
    box = data.get("box")
    if box is not None:
        if not isinstance(box, dict):
            raise TypeError("location.box must be an object")
        try:
            box = {key: box[key] for key in ("left", "top", "right", "bottom")}
        except KeyError as error:
            raise ValueError("location.box is missing required coordinates") from error
    return EvidenceLocation(
        box=None if box is None else BoundingBox(**box), crop_ref=data.get("crop_ref")
    )


def extracted_field_to_dict(field: ExtractedField) -> dict:
    return {
        "field_id": field.field_id.value,
        "state": field.state.value,
        "explanation": field.explanation,
        "observations": [
            {
                "raw_text": o.raw_text,
                "image_id": o.image_id,
                "parsed_value": _value_to_json(o.parsed_value),
                "location": _location_to_json(o.location),
            }
            for o in field.observations
        ],
    }


def extracted_field_from_dict(data: dict) -> ExtractedField:
    return _guard(
        lambda d: ExtractedField(
            field_id=FieldId(d["field_id"]),
            state=ExtractionState(d["state"]),
            explanation=d.get("explanation"),
            observations=tuple(
                Observation(
                    raw_text=o["raw_text"],
                    image_id=o["image_id"],
                    parsed_value=_value_from_json(o.get("parsed_value")),
                    location=_location_from_json(o.get("location")),
                )
                for o in d.get("observations", [])
            ),
        ),
        data,
        "extracted field",
    )


def warning_style_to_dict(style: WarningStyleObservation) -> dict:
    return {
        "image_id": style.image_id,
        "heading": style.heading.value,
        "body": style.body.value,
        "reason": style.reason,
    }


def warning_style_from_dict(data: dict) -> WarningStyleObservation:
    return _guard(
        lambda d: WarningStyleObservation(
            image_id=d["image_id"],
            heading=StyleJudgement(d["heading"]),
            body=StyleJudgement(d["body"]),
            reason=d.get("reason"),
        ),
        data,
        "warning style",
    )


def check_result_to_dict(result: CheckResult) -> dict:
    return {
        "check_id": result.check_id.value,
        "outcome": result.outcome.value,
        "field_id": None if result.field_id is None else result.field_id.value,
        "expected_value": _value_to_json(result.expected_value),
        "observed_value": _value_to_json(result.observed_value),
        "explanation": result.explanation,
        "evidence": [
            {
                "field_id": e.field_id.value,
                "observation_index": e.observation_index,
                "image_id": e.image_id,
            }
            for e in result.evidence
        ],
    }


def check_result_from_dict(data: dict) -> CheckResult:
    return _guard(
        lambda d: CheckResult(
            check_id=CheckId(d["check_id"]),
            outcome=CheckOutcome(d["outcome"]),
            field_id=None if d.get("field_id") is None else FieldId(d["field_id"]),
            expected_value=_value_from_json(d.get("expected_value")),
            observed_value=_value_from_json(d.get("observed_value")),
            explanation=d.get("explanation"),
            evidence=tuple(
                EvidenceRef(
                    FieldId(e["field_id"]), e["observation_index"], e["image_id"]
                )
                for e in d.get("evidence", [])
            ),
        ),
        data,
        "check result",
    )


def processing_error_to_dict(error: ProcessingError) -> dict:
    return {
        "stage": error.stage.value,
        "code": error.code.value,
        "message": error.message,
        "retryable": error.retryable,
    }


def processing_error_from_dict(data: dict) -> ProcessingError:
    return _guard(
        lambda d: ProcessingError(
            ProcessingStage(d["stage"]),
            ErrorCode(d["code"]),
            d["message"],
            d["retryable"],
        ),
        data,
        "processing error",
    )


def review_response_to_dict(response: ReviewResponse) -> dict:
    """Derived ``status`` and ``all_clear`` are included for readers only."""
    return {
        "application_id": response.application_id,
        "check_results": [check_result_to_dict(r) for r in response.check_results],
        "processing_errors": [
            processing_error_to_dict(e) for e in response.processing_errors
        ],
        "status": response.status.value,
        "all_clear": response.all_clear,
    }


def review_response_from_dict(data: dict) -> ReviewResponse:
    """Derived keys are ignored; status is always recomputed from the data."""
    return _guard(
        lambda d: ReviewResponse(
            d["application_id"],
            tuple(check_result_from_dict(r) for r in d.get("check_results", [])),
            tuple(
                processing_error_from_dict(e) for e in d.get("processing_errors", [])
            ),
        ),
        data,
        "review response",
    )


def validate_review_evidence(
    response: ReviewResponse,
    application: ApplicationData,
    extracted_fields: tuple[ExtractedField, ...] | list[ExtractedField],
) -> None:
    """Check that every evidence reference resolves; raise one ValueError.

    Run at the boundary where the application's images and the extracted
    observations are available. A reference must name a supplied image, an
    extracted field, an existing observation index, and the same image as
    that observation. All problems are listed together.
    """
    image_ids = {image.image_id for image in application.images}
    fields = {f.field_id: f for f in extracted_fields}
    problems = []
    for result in response.check_results:
        for ref in result.evidence:
            label = (
                f"{result.check_id.value} {ref.field_id.value}[{ref.observation_index}]"
            )
            field = fields.get(ref.field_id)
            if ref.image_id not in image_ids:
                problems.append(f"{label} names unsupplied image {ref.image_id!r}")
            if field is None:
                problems.append(f"{label} has no extracted field")
            elif ref.observation_index >= len(field.observations):
                problems.append(f"{label} has no such observation")
            elif field.observations[ref.observation_index].image_id != ref.image_id:
                problems.append(f"{label} image differs from the observation's image")
    if problems:
        raise ValueError("unresolved evidence references: " + "; ".join(problems))
