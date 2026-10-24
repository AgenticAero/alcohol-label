import pytest

from alcohol_label.comparison import (
    compare_brand,
    compare_class_type,
    compare_producer_name,
)
from alcohol_label.schemas import (
    CheckOutcome,
    ExtractedField,
    ExtractionState,
    FieldId,
    Observation,
)


def _observed(text: str) -> ExtractedField:
    return ExtractedField(
        FieldId.BRAND, ExtractionState.OBSERVED, (Observation(text, "front"),)
    )


def test_exact_match_has_evidence():
    result = compare_brand("Stone's Throw", _observed("Stone's Throw"))
    assert result.outcome is CheckOutcome.MATCH
    assert result.expected_value == result.observed_value == "Stone's Throw"
    assert result.evidence[0].image_id == "front"


def test_case_only_difference_matches_with_explanation():
    result = compare_brand("Stone's Throw", _observed("STONE\u2019S  THROW"))
    assert result.outcome is CheckOutcome.MATCH
    assert "normalization" in result.explanation
    assert result.observed_value == "STONE\u2019S  THROW"


def test_genuinely_different_brand_is_discrepancy():
    result = compare_brand("Stone's Throw", _observed("Stone's Throe"))
    assert result.outcome is CheckOutcome.DISCREPANCY
    assert result.evidence


def test_unknown_extraction_needs_review():
    uncertain = ExtractedField(
        FieldId.BRAND, ExtractionState.UNCERTAIN, (), "Text is blurred."
    )
    assert (
        compare_brand("Stone's Throw", uncertain).outcome is CheckOutcome.NEEDS_REVIEW
    )
    missing = ExtractedField(FieldId.BRAND, ExtractionState.MISSING, (), "Not found.")
    assert compare_brand("Stone's Throw", missing).outcome is CheckOutcome.NEEDS_REVIEW
    assert compare_brand("Stone's Throw", None).outcome is CheckOutcome.NEEDS_REVIEW


def test_shared_helpers_serve_other_checks():
    from alcohol_label.comparison import build_result, unresolved_result
    from alcohol_label.schemas import CheckId, EvidenceRef

    assert (
        unresolved_result(CheckId.CLASS_TYPE, None, None).outcome
        is CheckOutcome.NOT_EVALUATED
    )
    absent = unresolved_result(CheckId.CLASS_TYPE, "Bourbon", None)
    assert absent.outcome is CheckOutcome.NEEDS_REVIEW
    assert "class type" in absent.explanation

    conflicting = ExtractedField(
        FieldId.CLASS_TYPE,
        ExtractionState.CONFLICTING,
        (Observation("Rye", "front"), Observation("Bourbon", "back")),
        "Images differ.",
    )
    result = unresolved_result(CheckId.CLASS_TYPE, "Bourbon", conflicting)
    assert result.field_id is FieldId.CLASS_TYPE
    assert result.evidence == (
        EvidenceRef(FieldId.CLASS_TYPE, 0, "front"),
        EvidenceRef(FieldId.CLASS_TYPE, 1, "back"),
    )

    observed = ExtractedField(
        FieldId.CLASS_TYPE, ExtractionState.OBSERVED, (Observation("Bourbon", "front"),)
    )
    assert unresolved_result(CheckId.CLASS_TYPE, "Bourbon", observed) is None
    assert (
        build_result(CheckId.CLASS_TYPE, CheckOutcome.MATCH, "Bourbon", observed, None)
        .evidence[0]
        .image_id
        == "front"
    )


def _text_field(field_id: FieldId, text: str) -> ExtractedField:
    return ExtractedField(
        field_id, ExtractionState.OBSERVED, (Observation(text, "front"),)
    )


@pytest.mark.parametrize(
    ("compare", "field_id"),
    [
        (compare_class_type, FieldId.CLASS_TYPE),
        (compare_producer_name, FieldId.PRODUCER_NAME),
    ],
)
class TestTextFields:
    def test_equal_after_normalization_matches(self, compare, field_id):
        result = compare(
            "Straight Bourbon Whiskey",
            _text_field(field_id, "STRAIGHT  bourbon whiskey"),
        )
        assert result.outcome is CheckOutcome.MATCH
        assert result.explanation
        assert result.field_id is field_id
        assert result.evidence[0].image_id == "front"

    def test_exact_match_needs_no_note(self, compare, field_id):
        result = compare(
            "Example Distillery", _text_field(field_id, "Example Distillery")
        )
        assert result.outcome is CheckOutcome.MATCH
        assert result.explanation is None

    def test_different_value_is_discrepancy_with_both_values(self, compare, field_id):
        result = compare("Rye Whiskey", _text_field(field_id, "Bourbon Whiskey"))
        assert result.outcome is CheckOutcome.DISCREPANCY
        assert result.expected_value == "Rye Whiskey"
        assert result.observed_value == "Bourbon Whiskey"
        assert result.evidence

    def test_similar_value_is_not_fuzzy_matched(self, compare, field_id):
        result = compare(
            "Example Distillery", _text_field(field_id, "Example Distillers")
        )
        assert result.outcome is CheckOutcome.DISCREPANCY

    def test_missing_expected_is_not_evaluated(self, compare, field_id):
        result = compare(None, _text_field(field_id, "Bourbon"))
        assert result.outcome is CheckOutcome.NOT_EVALUATED

    def test_unknown_extraction_needs_review(self, compare, field_id):
        uncertain = ExtractedField(field_id, ExtractionState.UNCERTAIN, (), "Blurred.")
        assert compare("Bourbon", uncertain).outcome is CheckOutcome.NEEDS_REVIEW
        assert compare("Bourbon", None).outcome is CheckOutcome.NEEDS_REVIEW
