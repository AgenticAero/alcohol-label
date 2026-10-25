from io import BytesIO

import pytest
from PIL import Image

from alcohol_label.intake import UploadedImage, build_application
from alcohol_label.review import (
    review_after_extraction,
    review_without_extraction,
    unresolved_style_checks,
)
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
    StyleJudgement,
    Unit,
    WarningStyleObservation,
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
        FieldId.WARNING_TEXT: (
            "GOVERNMENT WARNING: (1) According to the Surgeon General, women "
            "should not drink alcoholic beverages during pregnancy because of "
            "the risk of birth defects. (2) Consumption of alcoholic beverages "
            "impairs your ability to drive a car or operate machinery, and may "
            "cause health problems."
        ),
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


def _style(heading="bold", body="not_bold", reason=None, image="front"):
    return WarningStyleObservation(
        image, StyleJudgement(heading), StyleJudgement(body), reason
    )


def test_review_without_style_leaves_style_checks_needs_review_not_a_pass():
    response = review_after_extraction(_application(), (), _fields())
    results = _results(response)

    for check in CheckId:
        if check in {CheckId.WARNING_HEADING_BOLD, CheckId.WARNING_BODY_NOT_BOLD}:
            assert results[check].outcome is CheckOutcome.NEEDS_REVIEW
        elif check is CheckId.COUNTRY_OF_ORIGIN:
            assert results[check].outcome is CheckOutcome.NOT_APPLICABLE
        else:
            assert results[check].outcome is CheckOutcome.MATCH, check
            assert results[check].evidence[0].image_id == "front"
    assert not response.all_clear


def test_review_is_all_clear_only_when_every_check_including_style_is_clear():
    response = review_after_extraction(_application(), (), _fields(), (_style(),))

    assert response.all_clear
    results = _results(response)
    assert results[CheckId.WARNING_HEADING_BOLD].outcome is CheckOutcome.MATCH
    assert results[CheckId.WARNING_BODY_NOT_BOLD].outcome is CheckOutcome.MATCH


@pytest.mark.parametrize(
    ("style", "heading", "body"),
    [
        (_style("not_bold", "not_bold"), CheckOutcome.DISCREPANCY, CheckOutcome.MATCH),
        (_style("bold", "bold"), CheckOutcome.MATCH, CheckOutcome.DISCREPANCY),
        (
            _style("uncertain", "bold", "Blurred."),
            CheckOutcome.NEEDS_REVIEW,
            CheckOutcome.DISCREPANCY,
        ),
    ],
)
def test_style_outcomes_are_reported_per_check_and_block_all_clear(
    style, heading, body
):
    response = review_after_extraction(_application(), (), _fields(), (style,))
    results = _results(response)

    assert results[CheckId.WARNING_HEADING_BOLD].outcome is heading
    assert results[CheckId.WARNING_BODY_NOT_BOLD].outcome is body
    assert not response.all_clear


def test_processing_error_still_prevents_style_comparison():
    error = ProcessingError(
        ProcessingStage.EXTRACTION, ErrorCode.PROVIDER_TIMEOUT, "Timed out.", True
    )
    response = review_after_extraction(_application(), (error,), _fields(), (_style(),))
    results = _results(response)

    for check in (CheckId.WARNING_HEADING_BOLD, CheckId.WARNING_BODY_NOT_BOLD):
        assert results[check].outcome is CheckOutcome.NOT_EVALUATED


def test_warning_conflict_across_images_needs_review_with_both_evidence_sources():
    fields = list(_fields())
    fields = [field for field in fields if field.field_id is not FieldId.WARNING_TEXT]
    fields.append(
        ExtractedField(
            FieldId.WARNING_TEXT,
            ExtractionState.CONFLICTING,
            (
                Observation("GOVERNMENT WARNING: The canonical text.", "front"),
                Observation("GOVERNMENT WARNING: A changed warning.", "back"),
            ),
            "Supplied images contain differing readings.",
        )
    )
    results = _results(review_after_extraction(_application(), (), tuple(fields)))

    for check in (CheckId.WARNING_WORDING, CheckId.WARNING_HEADING_CASE):
        assert results[check].outcome is CheckOutcome.NEEDS_REVIEW
        assert [item.image_id for item in results[check].evidence] == ["front", "back"]


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


def _style_items(styles, fields=None):
    response = review_after_extraction(
        _application(), (), fields or _fields(), tuple(styles)
    )
    return unresolved_style_checks(response, ["image-1", "image-2"])


def test_unresolved_style_checks_point_at_the_evidence_image():
    items = _style_items((_style("uncertain", "bold", "Blurred."),))

    assert [(r.check_id, ids) for r, ids in items] == [
        (CheckId.WARNING_HEADING_BOLD, ("front",))
    ]
    assert "Blurred." in items[0][0].explanation


def test_unresolved_style_without_evidence_offers_every_supplied_image():
    items = _style_items(())

    assert [r.check_id for r, _ in items] == [
        CheckId.WARNING_HEADING_BOLD,
        CheckId.WARNING_BODY_NOT_BOLD,
    ]
    assert all(ids == ("image-1", "image-2") for _, ids in items)


def test_resolved_style_checks_are_not_offered_for_visual_review():
    assert _style_items((_style(),)) == ()
    assert _style_items((_style("not_bold", "bold"),)) == ()
