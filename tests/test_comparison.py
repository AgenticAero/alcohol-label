from decimal import Decimal

import pytest

from alcohol_label.comparison import (
    compare_alcohol_content,
    compare_brand,
    compare_class_type,
    compare_country_of_origin,
    compare_net_contents,
    compare_producer_address,
    compare_producer_name,
    parse_percentages,
    parse_volumes,
    strip_origin_phrase,
)
from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    ExtractedField,
    ExtractionState,
    FieldId,
    Measurement,
    Observation,
    Unit,
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


def _abv(value: str) -> Measurement:
    return Measurement(Decimal(value), Unit.PERCENT_ABV)


def _abv_field(text: str) -> ExtractedField:
    return _text_field(FieldId.ALCOHOL_CONTENT, text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("45% Alc./Vol. (90 Proof)", (Decimal(45),)),
        ("Alc. 45.0 % by vol.", (Decimal("45.0"),)),
        ("45 percent alcohol by volume", (Decimal(45),)),
        ("45% / 45.0%", (Decimal(45),)),
        ("40% and 45%", (Decimal(40), Decimal(45))),
        ("90 Proof", ()),
    ],
)
def test_parse_percentages(text, expected):
    assert parse_percentages(text) == expected


@pytest.mark.parametrize("printed", ["45%", "45.0% Alc./Vol. (90 Proof)"])
def test_abv_equal_values_match(printed):
    result = compare_alcohol_content(_abv("45"), _abv_field(printed))
    assert result.outcome is CheckOutcome.MATCH
    assert result.observed_value == printed
    assert result.evidence[0].image_id == "front"
    assert compare_alcohol_content(_abv("45.0"), _abv_field("45%")).outcome is (
        CheckOutcome.MATCH
    )


def test_abv_different_value_is_discrepancy_showing_both():
    result = compare_alcohol_content(_abv("40"), _abv_field("45% Alc./Vol."))
    assert result.outcome is CheckOutcome.DISCREPANCY
    assert "45%" in result.explanation and "40%" in result.explanation
    assert result.expected_value == _abv("40")
    assert result.evidence


def test_abv_has_no_tolerance():
    result = compare_alcohol_content(_abv("45"), _abv_field("45.1%"))
    assert result.outcome is CheckOutcome.DISCREPANCY


def test_abv_proof_only_needs_review_even_if_proof_equals_double():
    result = compare_alcohol_content(_abv("45"), _abv_field("90 Proof"))
    assert result.outcome is CheckOutcome.NEEDS_REVIEW
    assert "proof" in result.explanation


def test_abv_proof_is_not_checked_against_percentage():
    result = compare_alcohol_content(_abv("45"), _abv_field("45% (80 Proof)"))
    assert result.outcome is CheckOutcome.MATCH


@pytest.mark.parametrize("printed", ["40% and 45%", "ALCOHOL BY VOLUME"])
def test_abv_conflicting_or_unparseable_needs_review(printed):
    result = compare_alcohol_content(_abv("45"), _abv_field(printed))
    assert result.outcome is CheckOutcome.NEEDS_REVIEW


def test_abv_missing_expected_and_unknown_extraction():
    assert (
        compare_alcohol_content(None, _abv_field("45%")).outcome
        is CheckOutcome.NOT_EVALUATED
    )
    assert compare_alcohol_content(_abv("45"), None).outcome is (
        CheckOutcome.NEEDS_REVIEW
    )
    conflicting = ExtractedField(
        FieldId.ALCOHOL_CONTENT,
        ExtractionState.CONFLICTING,
        (Observation("45%", "front"), Observation("40%", "back")),
        "Images differ.",
    )
    result = compare_alcohol_content(_abv("45"), conflicting)
    assert result.outcome is CheckOutcome.NEEDS_REVIEW
    assert len(result.evidence) == 2


def _volume(value: str, unit: Unit = Unit.MILLILITER) -> Measurement:
    return Measurement(Decimal(value), unit)


def _net(text: str) -> ExtractedField:
    return _text_field(FieldId.NET_CONTENTS, text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("750 mL", [(750, Unit.MILLILITER)]),
        ("750ML", [(750, Unit.MILLILITER)]),
        ("NET CONTENTS 0.75 L", [("0.75", Unit.LITER)]),
        ("1.75 Liters", [("1.75", Unit.LITER)]),
        ("750 mL / 25.4 FL. OZ.", [(750, Unit.MILLILITER), ("25.4", Unit.FLUID_OUNCE)]),
        ("25.4 fluid ounces", [("25.4", Unit.FLUID_OUNCE)]),
        ("75 cl", []),
        ("Louisville, KY 40202", []),
    ],
)
def test_parse_volumes(text, expected):
    parsed = [(v.value, v.unit) for v in parse_volumes(text)]
    assert parsed == [(Decimal(str(n)), u) for n, u in expected]


def test_fl_oz_converts_with_exact_factor():
    (volume,) = parse_volumes("10 fl oz")
    assert volume.millilitres == Decimal("295.735295625")


@pytest.mark.parametrize(
    "printed", ["750 mL", "750 mL / 25.4 fl oz", "0.75 L", "750 ML (25.4 FL. OZ.)"]
)
def test_net_contents_metric_statement_matches(printed):
    result = compare_net_contents(_volume("750"), _net(printed))
    assert result.outcome is CheckOutcome.MATCH
    assert result.observed_value == printed
    assert result.evidence[0].image_id == "front"


def test_net_contents_expected_in_litres_matches_millilitres():
    result = compare_net_contents(_volume("0.75", Unit.LITER), _net("750 mL"))
    assert result.outcome is CheckOutcome.MATCH


def test_net_contents_only_fl_oz_needs_review():
    result = compare_net_contents(_volume("750"), _net("25.4 fl oz"))
    assert result.outcome is CheckOutcome.NEEDS_REVIEW
    assert "metric" in result.explanation


def test_net_contents_different_metric_value_is_discrepancy():
    result = compare_net_contents(_volume("750"), _net("700 mL"))
    assert result.outcome is CheckOutcome.DISCREPANCY
    assert "700 ml" in result.explanation and "750 ml" in result.explanation
    assert result.evidence


def test_net_contents_secondary_fl_oz_never_changes_outcome():
    result = compare_net_contents(_volume("750"), _net("750 mL / 99 fl oz"))
    assert result.outcome is CheckOutcome.MATCH
    result = compare_net_contents(_volume("750"), _net("700 mL / 25.4 fl oz"))
    assert result.outcome is CheckOutcome.DISCREPANCY


@pytest.mark.parametrize("printed", ["75 cl", "ONE PINT", "700 mL and 750 mL"])
def test_net_contents_unsupported_or_conflicting_needs_review(printed):
    result = compare_net_contents(_volume("750"), _net(printed))
    assert result.outcome is CheckOutcome.NEEDS_REVIEW


def test_net_contents_missing_expected_and_unknown_extraction():
    assert compare_net_contents(None, _net("750 mL")).outcome is (
        CheckOutcome.NOT_EVALUATED
    )
    assert compare_net_contents(_volume("750"), None).outcome is (
        CheckOutcome.NEEDS_REVIEW
    )


def _address(text: str) -> ExtractedField:
    return _text_field(FieldId.PRODUCER_ADDRESS, text)


def _origin(text: str) -> ExtractedField:
    return _text_field(FieldId.COUNTRY_OF_ORIGIN, text)


def test_address_equal_after_normalization_matches():
    result = compare_producer_address("Louisville, KY", _address("LOUISVILLE,  KY"))
    assert result.outcome is CheckOutcome.MATCH
    assert result.evidence[0].image_id == "front"


def test_address_clear_difference_is_discrepancy_with_both_values():
    result = compare_producer_address("Louisville, KY", _address("Bardstown, KY"))
    assert result.outcome is CheckOutcome.DISCREPANCY
    assert (result.expected_value, result.observed_value) == (
        "Louisville, KY",
        "Bardstown, KY",
    )
    assert result.evidence


def test_address_appears_within_longer_printed_address_matches():
    full = _address("123 Main St, Louisville, KY")
    result = compare_producer_address("Louisville, KY", full)
    assert result.outcome is CheckOutcome.MATCH
    assert "within" in result.explanation
    assert result.observed_value == "123 Main St, Louisville, KY"


def test_address_containment_needs_whole_comma_segments_and_is_one_directional():
    assert (
        compare_producer_address(
            "Louisville, KY", _address("New Louisville, KY")
        ).outcome
        is CheckOutcome.DISCREPANCY
    )
    assert (
        compare_producer_address(
            "Louisville, KY", _address("123 Main St Louisville, KY")
        ).outcome
        is CheckOutcome.DISCREPANCY
    )
    assert (
        compare_producer_address("Louisville, KY", _address("Louisville, KYX")).outcome
        is CheckOutcome.DISCREPANCY
    )
    assert (
        compare_producer_address(
            "123 Main St, Louisville, KY", _address("Louisville, KY")
        ).outcome
        is CheckOutcome.DISCREPANCY
    )


@pytest.mark.parametrize(
    ("expected", "printed"),
    [
        ("123 Main Street", "123 Main St."),
        ("123 Main St", "123 MAIN STREET"),
        ("45 Oak Ave., Bardstown, KY", "45 Oak Avenue, Bardstown, KY"),
    ],
)
def test_address_street_type_abbreviations_match(expected, printed):
    result = compare_producer_address(expected, _address(printed))
    assert result.outcome is CheckOutcome.MATCH
    assert "street-type" in result.explanation


def test_address_other_abbreviations_are_not_expanded():
    assert (
        compare_producer_address(
            "Louisville, Kentucky", _address("Louisville, KY")
        ).outcome
        is CheckOutcome.DISCREPANCY
    )


def test_address_not_isolated_needs_review():
    combined = ExtractedField(
        FieldId.PRODUCER_ADDRESS,
        ExtractionState.UNCERTAIN,
        (Observation("BOTTLED BY EXAMPLE DISTILLERY LOUISVILLE KY", "front"),),
        "Name and address could not be separated.",
    )
    result = compare_producer_address("Louisville, KY", combined)
    assert result.outcome is CheckOutcome.NEEDS_REVIEW
    assert result.evidence
    assert (
        compare_producer_address(None, _address("Louisville, KY")).outcome
        is CheckOutcome.NOT_EVALUATED
    )


@pytest.mark.parametrize(
    "printed",
    ["Scotland", "Product of Scotland", "PRODUCE OF  SCOTLAND", "Made in Scotland"],
)
def test_origin_matches_with_recognized_leading_phrase(printed):
    result = compare_country_of_origin("Scotland", _origin(printed), True)
    assert result.outcome is CheckOutcome.MATCH
    assert result.observed_value == printed
    if printed != "Scotland":
        assert f'"{printed}"' in result.explanation
        assert '"SCOTLAND"' in result.explanation.upper()


@pytest.mark.parametrize(
    "printed",
    [
        "Bottled in Scotland",
        "Example Distillery, 1 High St, Speyside, Scotland",
        "Scotland-inspired",
        "Product of",
        "Ireland",
        "Product of Ireland",
    ],
)
def test_origin_differing_or_non_origin_text_is_a_discrepancy(printed):
    result = compare_country_of_origin("Scotland", _origin(printed), True)
    assert result.outcome is CheckOutcome.DISCREPANCY
    assert result.evidence


def test_origin_not_observed_for_import_needs_review_requesting_evidence():
    missing = ExtractedField(
        FieldId.COUNTRY_OF_ORIGIN, ExtractionState.MISSING, (), "No reading."
    )
    for extracted in (missing, None):
        result = compare_country_of_origin("Scotland", extracted, True)
        assert result.outcome is CheckOutcome.NEEDS_REVIEW
        assert "additional evidence" in result.explanation


def test_origin_phrase_removal_is_limited_to_the_start_of_the_text():
    assert strip_origin_phrase("Scotland Product of") == "Scotland Product of"
    assert strip_origin_phrase("Product of Scotland") == "Scotland"


def test_origin_domestic_is_not_applicable_even_with_a_reading():
    assert (
        compare_country_of_origin(None, None, False).outcome
        is CheckOutcome.NOT_APPLICABLE
    )
    result = compare_country_of_origin("Scotland", _origin("Scotland"), False)
    assert result.outcome is CheckOutcome.NOT_APPLICABLE


def test_origin_imported_unresolved_cases():
    assert (
        compare_country_of_origin(None, _origin("Scotland"), True).outcome
        is CheckOutcome.NOT_EVALUATED
    )
    assert (
        compare_country_of_origin("Scotland", None, True).outcome
        is CheckOutcome.NEEDS_REVIEW
    )
    conflicting = ExtractedField(
        FieldId.COUNTRY_OF_ORIGIN,
        ExtractionState.CONFLICTING,
        (Observation("Scotland", "front"), Observation("Ireland", "back")),
        "Images differ.",
    )
    assert (
        compare_country_of_origin("Scotland", conflicting, True).outcome
        is CheckOutcome.NEEDS_REVIEW
    )


# One row per field: (check, compare(expected, extracted), expected, matching text, differing text).
_MATRIX = [
    (CheckId.BRAND, compare_brand, "Stone's Throw", "STONE'S THROW", "Stone's Throe"),
    (CheckId.CLASS_TYPE, compare_class_type, "Bourbon", "bourbon", "Rye"),
    (CheckId.ALCOHOL_CONTENT, compare_alcohol_content, _abv("45"), "45%", "40%"),
    (CheckId.NET_CONTENTS, compare_net_contents, _volume("750"), "750 mL", "700 mL"),
    (
        CheckId.PRODUCER_NAME,
        compare_producer_name,
        "Example Distillery",
        "EXAMPLE DISTILLERY",
        "Other Distillery",
    ),
    (
        CheckId.PRODUCER_ADDRESS,
        compare_producer_address,
        "Louisville, KY",
        "louisville,  ky",
        "Bardstown, KY",
    ),
    (
        CheckId.COUNTRY_OF_ORIGIN,
        lambda expected, extracted: compare_country_of_origin(
            expected, extracted, True
        ),
        "Scotland",
        "Product of Scotland",
        "Ireland",
    ),
]
_MATRIX_IDS = [row[0].value for row in _MATRIX]


def _matrix_field(check: CheckId, text: str) -> ExtractedField:
    return _text_field(FieldId(check.value), text)


@pytest.mark.parametrize(
    ("check", "compare", "expected", "match", "_"), _MATRIX, ids=_MATRIX_IDS
)
def test_every_field_matches_with_evidence(check, compare, expected, match, _):
    result = compare(expected, _matrix_field(check, match))
    assert result.outcome is CheckOutcome.MATCH
    assert result.check_id is check
    assert result.expected_value == expected
    assert result.observed_value == match
    assert [e.image_id for e in result.evidence] == ["front"]


@pytest.mark.parametrize(
    ("check", "compare", "expected", "_", "differ"), _MATRIX, ids=_MATRIX_IDS
)
def test_every_field_reports_a_discrepancy_with_both_values(
    check, compare, expected, _, differ
):
    result = compare(expected, _matrix_field(check, differ))
    assert result.outcome is CheckOutcome.DISCREPANCY
    assert result.expected_value == expected
    assert result.observed_value == differ
    assert result.evidence
    assert result.explanation


@pytest.mark.parametrize(
    ("check", "compare", "expected", "match", "_"), _MATRIX, ids=_MATRIX_IDS
)
def test_every_field_without_an_expected_value_is_not_evaluated(
    check, compare, expected, match, _
):
    result = compare(None, _matrix_field(check, match))
    assert result.outcome is CheckOutcome.NOT_EVALUATED
    assert "not supplied" in result.explanation


@pytest.mark.parametrize(
    ("check", "compare", "expected", "match", "differ"), _MATRIX, ids=_MATRIX_IDS
)
@pytest.mark.parametrize("state", ["absent", "missing", "uncertain", "conflicting"])
def test_every_field_with_unresolved_extraction_needs_review(
    check, compare, expected, match, differ, state
):
    field_id = FieldId(check.value)
    extracted = {
        "absent": None,
        "missing": ExtractedField(field_id, ExtractionState.MISSING, (), "Not found."),
        "uncertain": ExtractedField(
            field_id,
            ExtractionState.UNCERTAIN,
            (Observation(match, "front"),),
            "Blurred.",
        ),
        "conflicting": ExtractedField(
            field_id,
            ExtractionState.CONFLICTING,
            (Observation(match, "front"), Observation(differ, "back")),
            "Images differ.",
        ),
    }[state]

    result = compare(expected, extracted)

    assert result.outcome is CheckOutcome.NEEDS_REVIEW
    assert result.explanation
    expected_images = {
        "absent": [],
        "missing": [],
        "uncertain": ["front"],
        "conflicting": ["front", "back"],
    }[state]
    assert [e.image_id for e in result.evidence] == expected_images
