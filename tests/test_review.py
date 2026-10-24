from io import BytesIO

from PIL import Image

from alcohol_label.intake import UploadedImage, build_application
from alcohol_label.review import review_after_extraction, review_without_extraction
from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    ErrorCode,
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


def test_review_compares_brand_only_and_keeps_other_checks_unresolved():
    from alcohol_label.schemas import (
        ExtractedField,
        ExtractionState,
        FieldId,
        Observation,
    )

    field = ExtractedField(
        FieldId.BRAND,
        ExtractionState.OBSERVED,
        (Observation("STONE'S THROW", "front"),),
    )
    response = review_after_extraction(_application(), (), (field,))
    results = {r.check_id: r for r in response.check_results}
    assert results[CheckId.BRAND].outcome is CheckOutcome.MATCH
    assert results[CheckId.CLASS_TYPE].outcome is CheckOutcome.NOT_EVALUATED
    assert not response.all_clear
