"""Check results while field comparison is not implemented."""

from alcohol_label.comparison import compare_brand
from alcohol_label.schemas import (
    ApplicationData,
    CheckId,
    CheckOutcome,
    CheckResult,
    FieldId,
    ReviewResponse,
)

_NO_EXTRACTION = "Label extraction has not been run, so this check was not run."
_NO_COMPARISON = "Label fields were extracted, but comparison is not implemented yet."
_EXTRACTION_FAILED = (
    "Extraction failed for one or more images, so this check was not run."
)


def _field_for(check_id: CheckId) -> FieldId:
    try:
        return FieldId(check_id.value)
    except ValueError:
        return FieldId.WARNING_TEXT


def review_without_extraction(application: ApplicationData) -> ReviewResponse:
    """Report every check as not evaluated before extraction."""
    return _pending_review(application, _NO_EXTRACTION)


def review_after_extraction(
    application: ApplicationData,
    processing_errors=(),
    fields=(),
) -> ReviewResponse:
    """Compare brand; every other check stays not evaluated."""
    pending_reason = _EXTRACTION_FAILED if processing_errors else _NO_COMPARISON
    extracted = {f.field_id: f for f in fields}
    compare = not processing_errors
    return _pending_review(
        application,
        pending_reason,
        processing_errors,
        extracted.get(FieldId.BRAND) if compare else None,
        compare,
    )


def _pending_review(
    application: ApplicationData,
    pending_reason: str,
    processing_errors=(),
    brand_field=None,
    compare_brand_check: bool = False,
) -> ReviewResponse:
    missing = set(application.missing_required_fields())
    results = []
    for check_id in CheckId:
        field_id = _field_for(check_id)
        if check_id is CheckId.BRAND and compare_brand_check:
            results.append(compare_brand(application.brand, brand_field))
            continue
        if check_id is CheckId.COUNTRY_OF_ORIGIN and not application.is_imported:
            outcome = CheckOutcome.NOT_APPLICABLE
            reason = "Product is not imported, so country of origin is not required."
        elif field_id in missing:
            outcome = CheckOutcome.NOT_EVALUATED
            reason = f"Expected {field_id.value.replace('_', ' ')} was not supplied."
        else:
            outcome = CheckOutcome.NOT_EVALUATED
            reason = pending_reason
        results.append(
            CheckResult(
                check_id=check_id,
                outcome=outcome,
                field_id=field_id,
                explanation=reason,
            )
        )
    return ReviewResponse(
        application.application_id,
        tuple(results),
        tuple(processing_errors),
    )
