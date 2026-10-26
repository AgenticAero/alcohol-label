# Copyright (c) 2026 John Michael Egan. All rights reserved.
# Hiring evaluation permitted under the LICENSE file at the repository root.
"""Check results: field and warning comparisons after extraction."""

from collections.abc import Sequence

from alcohol_label.comparison import (
    compare_alcohol_content,
    compare_brand,
    compare_class_type,
    compare_country_of_origin,
    compare_net_contents,
    compare_producer_address,
    compare_producer_name,
    compare_warning_body_not_bold,
    compare_warning_heading_bold,
    compare_warning_heading_case,
    compare_warning_wording,
)
from alcohol_label.schemas import (
    ApplicationData,
    CheckId,
    CheckOutcome,
    CheckResult,
    FieldId,
    ReviewResponse,
)

_NO_EXTRACTION = "Label extraction has not been run, so this check was not run."
_EXTRACTION_FAILED = (
    "Extraction failed for one or more images, so this check was not run."
)

_COMPARATORS = {
    CheckId.BRAND: lambda app, field: compare_brand(app.brand, field),
    CheckId.CLASS_TYPE: lambda app, field: compare_class_type(app.class_type, field),
    CheckId.ALCOHOL_CONTENT: lambda app, field: compare_alcohol_content(
        app.alcohol_content, field
    ),
    CheckId.NET_CONTENTS: lambda app, field: compare_net_contents(
        app.net_contents, field
    ),
    CheckId.PRODUCER_NAME: lambda app, field: compare_producer_name(
        app.producer_name, field
    ),
    CheckId.PRODUCER_ADDRESS: lambda app, field: compare_producer_address(
        app.producer_address, field
    ),
    CheckId.COUNTRY_OF_ORIGIN: lambda app, field: compare_country_of_origin(
        app.country_of_origin, field, app.is_imported
    ),
}
_WARNING_COMPARATORS = {
    CheckId.WARNING_WORDING: compare_warning_wording,
    CheckId.WARNING_HEADING_CASE: compare_warning_heading_case,
}
_STYLE_COMPARATORS = {
    CheckId.WARNING_HEADING_BOLD: compare_warning_heading_bold,
    CheckId.WARNING_BODY_NOT_BOLD: compare_warning_body_not_bold,
}


def _field_for(check_id: CheckId) -> FieldId:
    try:
        return FieldId(check_id.value)
    except ValueError:
        return FieldId.WARNING_TEXT


def review_without_extraction(application: ApplicationData) -> ReviewResponse:
    """Report every check as not evaluated before extraction."""
    return _review(application, _NO_EXTRACTION)


def review_after_extraction(
    application: ApplicationData,
    processing_errors=(),
    fields=(),
    warning_styles=(),
) -> ReviewResponse:
    """Run the field, warning text and warning style comparisons.

    Any processing error prevents every comparison. Style that was not
    returned or is unclear stays needs_review, so it is never a pass.
    """
    if processing_errors:
        return _review(application, _EXTRACTION_FAILED, processing_errors)
    extracted = {f.field_id: f for f in fields}
    return _review(application, _NO_EXTRACTION, (), extracted, tuple(warning_styles))


def _review(
    application: ApplicationData,
    pending_reason: str,
    processing_errors=(),
    extracted=None,
    warning_styles=(),
) -> ReviewResponse:
    missing = set(application.missing_required_fields())
    results = []
    for check_id in CheckId:
        field_id = _field_for(check_id)
        domestic_origin = (
            check_id is CheckId.COUNTRY_OF_ORIGIN and not application.is_imported
        )
        if extracted is not None and check_id in _COMPARATORS and not domestic_origin:
            results.append(_COMPARATORS[check_id](application, extracted.get(field_id)))
            continue
        if extracted is not None and check_id in _WARNING_COMPARATORS:
            results.append(_WARNING_COMPARATORS[check_id](extracted.get(field_id)))
            continue
        if extracted is not None and check_id in _STYLE_COMPARATORS:
            results.append(
                _STYLE_COMPARATORS[check_id](warning_styles, extracted.get(field_id))
            )
            continue
        if domestic_origin:
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


def unresolved_style_checks(
    response: ReviewResponse, all_image_ids: Sequence[str]
) -> tuple[tuple[CheckResult, tuple[str, ...]], ...]:
    """Style checks needing review, each with the image IDs a reviewer should open.

    Uses the result's evidence images; with none, every supplied image.
    """
    items = []
    for result in response.check_results:
        if (
            result.check_id in _STYLE_COMPARATORS
            and result.outcome is CheckOutcome.NEEDS_REVIEW
        ):
            evidence_ids = tuple(dict.fromkeys(e.image_id for e in result.evidence))
            items.append((result, evidence_ids or tuple(all_image_ids)))
    return tuple(items)
