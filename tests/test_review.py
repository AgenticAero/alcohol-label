from io import BytesIO

import pytest
from PIL import Image

from alcohol_label.intake import UploadedImage, build_application
from alcohol_label.review import review_after_extraction, review_without_extraction
from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    ErrorCode,
    ExtractedField,
    ExtractionState,
    FieldId,
    Observation,
    ProcessingError,
    ProcessingStage,
    Unit,
)


def _application(**overrides):
    buffer = BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="PNG")
    values = {
        "application_id": "APP-1",
        "brand": "Stone's Throw",
        "class_type": "Bourbon",
        "alcohol_content": "45",
        "net_contents": "750",
        "net_contents_unit": Unit.MILLILITER,
        "producer_name": "Stone Distilling",
        "producer_address": "Louisville, KY",
        "is_imported": False,
        "country_of_origin": "",
        "uploads": [UploadedImage("front.png", buffer.getvalue())],
    }
    values.update(overrides)
    return build_application(**values).application


def _review(**overrides):
    application = _application(**overrides)
    response = review_without_extraction(application)
    return {r.check_id: r for r in response.check_results}, response


def test_nothing_is_a_match_or_all_clear_without_extraction():
    results, response = _review()
    assert len(results) == len(CheckId)
    assert CheckOutcome.MATCH not in {r.outcome for r in results.values()}
    assert not response.all_clear


def test_missing_value_is_not_evaluated_with_reason():
    results, _ = _review(brand="")
    brand = results[CheckId.BRAND]
    assert brand.outcome is CheckOutcome.NOT_EVALUATED
    assert "not supplied" in brand.explanation


def test_country_not_applicable_for_domestic_but_unresolved_for_import():
    domestic, _ = _review()
    assert domestic[CheckId.COUNTRY_OF_ORIGIN].outcome is CheckOutcome.NOT_APPLICABLE
    imported, response = _review(is_imported=True)
    country = imported[CheckId.COUNTRY_OF_ORIGIN]
    assert country.outcome is CheckOutcome.NOT_EVALUATED
    assert "not supplied" in country.explanation
    assert not response.all_clear


def test_review_after_extraction_keeps_checks_unresolved_and_errors_separate():
    application = _application()
    processing_error = ProcessingError(
        ProcessingStage.EXTRACTION,
        ErrorCode.PROVIDER_TIMEOUT,
        "Provider timed out.",
        True,
    )

    response = review_after_extraction(application, (processing_error,))

    assert all(
        result.outcome is not CheckOutcome.MATCH for result in response.check_results
    )
    assert all(
        "Extraction failed" in result.explanation
        for result in response.check_results
        if result.outcome is CheckOutcome.NOT_EVALUATED
        and result.check_id is not CheckId.COUNTRY_OF_ORIGIN
    )
    assert response.processing_errors == (processing_error,)
    assert not response.all_clear


def _fields(**texts):
    values = {
        FieldId.BRAND: "STONE'S THROW",
        FieldId.CLASS_TYPE: "bourbon",
        FieldId.ALCOHOL_CONTENT: "45.0% Alc./Vol. (90 Proof)",
        FieldId.NET_CONTENTS: "750 mL / 25.4 FL. OZ.",
        FieldId.PRODUCER_NAME: "Stone Distilling",
        FieldId.PRODUCER_ADDRESS: "Louisville, KY",
        FieldId.COUNTRY_OF_ORIGIN: None,
    }
    values.update({FieldId(k): v for k, v in texts.items()})
    fields = []
    for field_id, text in values.items():
        if text is None:
            fields.append(
                ExtractedField(field_id, ExtractionState.MISSING, (), "Not printed.")
            )
        else:
            fields.append(
                ExtractedField(
                    field_id, ExtractionState.OBSERVED, (Observation(text, "front"),)
                )
            )
    return tuple(fields)


def _results(response):
    return {r.check_id: r for r in response.check_results}


WARNING_CHECKS = (
    CheckId.WARNING_WORDING,
    CheckId.WARNING_HEADING_CASE,
    CheckId.WARNING_HEADING_BOLD,
    CheckId.WARNING_BODY_NOT_BOLD,
)


def test_review_runs_every_field_comparison_and_leaves_warnings_unevaluated():
    response = review_after_extraction(_application(), (), _fields())
    results = _results(response)

    for check in CheckId:
        if check in WARNING_CHECKS:
            assert results[check].outcome is CheckOutcome.NOT_EVALUATED
        elif check is CheckId.COUNTRY_OF_ORIGIN:
            assert results[check].outcome is CheckOutcome.NOT_APPLICABLE
        else:
            assert results[check].outcome is CheckOutcome.MATCH, check
            assert results[check].evidence[0].image_id == "front"
    assert not response.all_clear


@pytest.mark.parametrize(
    ("field", "text", "check"),
    [
        ("brand", "Another Brand", CheckId.BRAND),
        ("class_type", "Rye", CheckId.CLASS_TYPE),
        ("alcohol_content", "40%", CheckId.ALCOHOL_CONTENT),
        ("net_contents", "700 mL", CheckId.NET_CONTENTS),
        ("producer_name", "Other Distilling", CheckId.PRODUCER_NAME),
        ("producer_address", "Bardstown, KY", CheckId.PRODUCER_ADDRESS),
    ],
)
def test_a_differing_label_value_is_reported_on_its_own_check(field, text, check):
    response = review_after_extraction(_application(), (), _fields(**{field: text}))
    results = _results(response)

    assert results[check].outcome is CheckOutcome.DISCREPANCY
    assert results[check].evidence
    others = {
        c
        for c, r in results.items()
        if r.outcome is CheckOutcome.DISCREPANCY and c is not check
    }
    assert others == set()


def test_missing_expected_value_is_not_evaluated_even_with_a_label_reading():
    results = _results(
        review_after_extraction(_application(class_type=""), (), _fields())
    )
    assert results[CheckId.CLASS_TYPE].outcome is CheckOutcome.NOT_EVALUATED
    assert "not supplied" in results[CheckId.CLASS_TYPE].explanation


def test_field_without_extraction_needs_review_not_a_pass():
    fields = tuple(f for f in _fields() if f.field_id is not FieldId.NET_CONTENTS)
    results = _results(review_after_extraction(_application(), (), fields))
    assert results[CheckId.NET_CONTENTS].outcome is CheckOutcome.NEEDS_REVIEW


def test_imported_origin_is_compared_and_domestic_stays_not_applicable():
    imported = _application(is_imported=True, country_of_origin="Scotland")
    results = _results(
        review_after_extraction(
            imported, (), _fields(country_of_origin="Product of Scotland")
        )
    )
    assert results[CheckId.COUNTRY_OF_ORIGIN].outcome is CheckOutcome.MATCH

    results = _results(review_after_extraction(imported, (), _fields()))
    country = results[CheckId.COUNTRY_OF_ORIGIN]
    assert country.outcome is CheckOutcome.NEEDS_REVIEW
    assert "additional evidence" in country.explanation

    domestic = _application(country_of_origin="Scotland")
    results = _results(
        review_after_extraction(domestic, (), _fields(country_of_origin="Scotland"))
    )
    assert results[CheckId.COUNTRY_OF_ORIGIN].outcome is CheckOutcome.NOT_APPLICABLE


def test_processing_error_prevents_every_comparison_even_with_fields():
    error = ProcessingError(
        ProcessingStage.EXTRACTION, ErrorCode.PROVIDER_TIMEOUT, "Timed out.", True
    )
    response = review_after_extraction(_application(), (error,), _fields())
    for result in response.check_results:
        assert result.outcome in {
            CheckOutcome.NOT_EVALUATED,
            CheckOutcome.NOT_APPLICABLE,
        }
        assert not result.evidence
    assert response.processing_errors == (error,)
