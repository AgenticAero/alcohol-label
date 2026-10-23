"""Turn raw form values and uploaded files into validated application data.

Independent of the UI. Problems come back as readable messages rather than
exceptions; deeper defensive handling belongs to AL-16.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO

from PIL import Image

from alcohol_label.schemas import (
    ApplicationData,
    BeverageCategory,
    FieldId,
    ImageReference,
    Measurement,
    Unit,
)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGES = 2
_ALLOWED_FORMATS = frozenset({"JPEG", "PNG"})


@dataclass(frozen=True, slots=True)
class UploadedImage:
    """One uploaded file as received from the UI."""

    name: str
    data: bytes


@dataclass(frozen=True, slots=True)
class IntakeResult:
    """Parsed application, or ``None`` with the reasons it could not be built.

    ``application`` is set only when ``errors`` is empty. Blank expected values
    are not errors; they stay ``None`` and surface through
    ``ApplicationData.missing_required_fields``.
    """

    application: ApplicationData | None
    errors: tuple[str, ...]
    missing_fields: tuple[FieldId, ...] = ()


def _blank_to_none(text: str | None) -> str | None:
    if text is None or not text.strip():
        return None
    return text.strip()


def parse_measurement(label: str, text: str | None, unit: Unit) -> Measurement | str:
    """Return a Measurement, or an error message; blank handling is the caller's."""
    try:
        value = Decimal((text or "").strip())
    except InvalidOperation:
        return f"{label} must be a number."
    if not value.is_finite():
        return f"{label} must be a finite number."
    if value <= 0:
        return f"{label} must be greater than zero."
    return Measurement(value, unit)


def _optional_measurement(
    label: str, text: str | None, unit: Unit, errors: list[str]
) -> Measurement | None:
    if _blank_to_none(text) is None:
        return None
    parsed = parse_measurement(label, text, unit)
    if isinstance(parsed, str):
        errors.append(parsed)
        return None
    return parsed


def validate_uploads(
    uploads: list[UploadedImage],
) -> tuple[tuple[ImageReference, ...], tuple[str, ...]]:
    """Validate one or two JPEG/PNG uploads and return references with IDs."""
    if not uploads:
        return (), ("Upload at least one label image.",)
    if len(uploads) > MAX_IMAGES:
        return (), (f"Upload at most {MAX_IMAGES} label images.",)

    references: list[ImageReference] = []
    errors: list[str] = []
    for index, upload in enumerate(uploads, start=1):
        name = upload.name.strip() or f"image-{index}"
        problem = _image_problem(upload.data)
        if problem:
            errors.append(f"{name}: {problem}")
        else:
            references.append(ImageReference(f"image-{index}", name))
    if errors:
        return (), tuple(errors)
    return tuple(references), ()


def _image_problem(data: bytes) -> str | None:
    if len(data) > MAX_IMAGE_BYTES:
        return f"file is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MiB."
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in _ALLOWED_FORMATS:
                return "unsupported format; use JPEG or PNG."
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                return f"image exceeds {MAX_IMAGE_PIXELS // 1_000_000} megapixels."
            image.verify()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return "file is not a readable image."
    return None


def build_application(
    *,
    application_id: str,
    brand: str | None,
    class_type: str | None,
    alcohol_content: str | None,
    net_contents: str | None,
    net_contents_unit: Unit,
    producer_name: str | None,
    producer_address: str | None,
    is_imported: bool,
    country_of_origin: str | None,
    uploads: list[UploadedImage],
) -> IntakeResult:
    """Build ``ApplicationData`` from raw form values and uploads."""
    errors: list[str] = []
    if _blank_to_none(application_id) is None:
        errors.append("Application ID is required.")
    alcohol = _optional_measurement(
        "Alcohol content", alcohol_content, Unit.PERCENT_ABV, errors
    )
    net = _optional_measurement("Net contents", net_contents, net_contents_unit, errors)
    images, image_errors = validate_uploads(uploads)
    errors.extend(image_errors)
    required = [
        (FieldId.BRAND, brand),
        (FieldId.CLASS_TYPE, class_type),
        (FieldId.ALCOHOL_CONTENT, alcohol_content),
        (FieldId.NET_CONTENTS, net_contents),
        (FieldId.PRODUCER_NAME, producer_name),
        (FieldId.PRODUCER_ADDRESS, producer_address),
    ]
    if is_imported:
        required.append((FieldId.COUNTRY_OF_ORIGIN, country_of_origin))
    missing = tuple(f for f, text in required if _blank_to_none(text) is None)
    if errors:
        return IntakeResult(None, tuple(errors), missing)

    application = ApplicationData(
        application_id=application_id.strip(),
        beverage_category=BeverageCategory.DISTILLED_SPIRITS,
        is_imported=is_imported,
        images=images,
        brand=_blank_to_none(brand),
        class_type=_blank_to_none(class_type),
        alcohol_content=alcohol,
        net_contents=net,
        producer_name=_blank_to_none(producer_name),
        producer_address=_blank_to_none(producer_address),
        country_of_origin=_blank_to_none(country_of_origin),
    )
    return IntakeResult(application, (), missing)
