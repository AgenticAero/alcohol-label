"""Check results for a review that has no label extraction yet."""

from alcohol_label.schemas import (
    ApplicationData,
    CheckId,
    CheckOutcome,
    CheckResult,
    FieldId,
    ReviewResponse,
)

_PENDING = "Label extraction is not implemented yet, so this check was not run."


def _field_for(check_id: CheckId) -> FieldId:
    try:
        return FieldId(check_id.value)
    except ValueError:
        return FieldId.WARNING_TEXT


def review_without_extraction(application: ApplicationData) -> ReviewResponse:
    """Report every check as not evaluated; only a domestic country check is not applicable."""
    missing = set(application.missing_required_fields())
    results = []
    for check_id in CheckId:
        field_id = _field_for(check_id)
        if check_id is CheckId.COUNTRY_OF_ORIGIN and not application.is_imported:
            outcome = CheckOutcome.NOT_APPLICABLE
            reason = "Product is not imported, so country of origin is not required."
        elif field_id in missing:
            outcome = CheckOutcome.NOT_EVALUATED
            reason = f"Expected {field_id.value.replace('_', ' ')} was not supplied."
        else:
            outcome = CheckOutcome.NOT_EVALUATED
            reason = _PENDING
        results.append(
            CheckResult(
                check_id=check_id,
                outcome=outcome,
                field_id=field_id,
                explanation=reason,
            )
        )
    return ReviewResponse(application.application_id, tuple(results))
