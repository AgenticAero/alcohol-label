import hashlib
import re
from decimal import Decimal

import pytest
from PIL import Image

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
    ErrorCode,
    ExtractedField,
    ExtractionState,
    FieldId,
    Observation,
    StyleJudgement,
    WarningStyleObservation,
    application_from_dict,
    application_to_dict,
)

from .support import FIXTURES, REFERENCES, SCENARIOS, STARTERS


def _application(scenario_id: str) -> dict:
    return SCENARIOS[scenario_id]["application"]


def _differences(a: dict, b: dict) -> set[str]:
    return {key for key in a if a[key] != b[key]}


_WARNING_CHECKS = (
    "warning_wording",
    "warning_heading_case",
    "warning_heading_bold",
    "warning_body_not_bold",
)


def _images_of(scenario: dict) -> list[dict]:
    return [STARTERS[f] for f in scenario["image_files"]]


def _is_simple(scenario: dict) -> bool:
    """One image, every statement legible, warning printed: checked field by field."""
    (image,) = _images_of(scenario) if len(scenario["image_files"]) == 1 else (None,)
    return (
        image is not None
        and not image.get("illegible_fields")
        and "provider_failure" not in scenario
        and image["visible_text"]["warning_heading"] is not None
    )


SIMPLE_SCENARIOS = {sid: s for sid, s in SCENARIOS.items() if _is_simple(s)}


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_applications_are_valid_and_canonical(scenario):
    data = scenario["application"]

    application = application_from_dict(data)

    assert isinstance(application, ApplicationData)
    assert application_to_dict(application) == data
    assert application.application_id == scenario["scenario_id"]
    assert application.missing_required_fields() == ()


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_scenario_images_exist_and_match_application_references(scenario):
    uris = [image["uri"] for image in scenario["application"]["images"]]
    files = [f"tests/fixtures/{f}" for f in scenario["image_files"]]

    assert uris == files
    assert all(f in STARTERS for f in scenario["image_files"])
    assert all((FIXTURES / f).is_file() for f in scenario["image_files"])
    assert scenario["split"] == "development"


def test_every_stored_image_is_listed_once_with_matching_file_facts():
    listed = {**STARTERS, **REFERENCES}
    assert len(listed) == len(STARTERS) + len(REFERENCES)
    stored = {f"labels/{p.name}" for p in (FIXTURES / "labels").iterdir()}
    assert stored == set(listed)

    for name, entry in listed.items():
        path = FIXTURES / name
        with Image.open(path) as image:
            assert (image.format, image.width, image.height) == (
                entry["format"],
                entry["width"],
                entry["height"],
            ), name
        data = path.read_bytes()
        assert len(data) == entry["bytes"], name
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], name


def test_starters_are_synthetic_and_references_have_sources():
    for entry in STARTERS.values():
        assert entry["provenance"]["type"] == "synthetic"
        assert entry["provenance"]["generator"].strip()
        assert entry["provenance"]["permitted_use"].strip()
    for name, entry in REFERENCES.items():
        assert entry["source_url"].startswith("https://"), name
        assert "srsltid" not in entry["source_url"], name
        assert entry["permission"].strip(), name
    used = {f for s in SCENARIOS.values() for f in s["image_files"]}
    assert used.isdisjoint(REFERENCES)


def test_expected_outcomes_cover_every_check_with_valid_outcomes():
    for scenario in SCENARIOS.values():
        outcomes = scenario["expected_outcomes"]
        assert set(outcomes) == {c.value for c in CheckId}
        assert {CheckOutcome(o) for o in outcomes.values()}
        country = outcomes["country_of_origin"]
        imported = scenario["application"]["is_imported"]
        assert (country == "not_applicable") is (not imported)


def test_starter_scenarios_cover_required_comparison_and_warning_cases():
    baseline = _application("S01-clear-match")
    assert {
        "S01-clear-match",
        "S02-brand-case-only",
        "S03-abv-mismatch",
        "S04-warning-text-changed",
        "S16-warning-heading-title-case",
    } <= set(SCENARIOS)
    other_than_match = {
        sid: {c for c, o in s["expected_outcomes"].items() if o != "match"}
        for sid, s in SCENARIOS.items()
    }
    assert other_than_match["S01-clear-match"] == {"country_of_origin"}
    assert other_than_match["S02-brand-case-only"] == {"country_of_origin"}
    assert other_than_match["S03-abv-mismatch"] == {
        "country_of_origin",
        "alcohol_content",
    }
    assert other_than_match["S04-warning-text-changed"] == {
        "country_of_origin",
        "warning_wording",
    }
    assert other_than_match["S16-warning-heading-title-case"] == {
        "country_of_origin",
        "warning_wording",
        "warning_heading_case",
    }

    brand_case = _application("S02-brand-case-only")
    assert _differences(baseline, brand_case) == {"application_id", "brand"}
    assert baseline["brand"] != brand_case["brand"]
    assert baseline["brand"].casefold() == brand_case["brand"].casefold()

    abv = _application("S03-abv-mismatch")
    assert _differences(baseline, abv) == {"application_id", "alcohol_content"}

    warning = _application("S04-warning-text-changed")
    assert _differences(baseline, warning) == {"application_id", "images"}
    assert SCENARIOS["S04-warning-text-changed"]["deliberate_defect"]


def test_annotations_agree_with_the_applications_and_the_warning_change():
    clear = STARTERS["labels/starter-clear.png"]["visible_text"]
    changed = STARTERS["labels/starter-warning-changed.png"]["visible_text"]
    expected = _application("S01-clear-match")

    assert clear["brand"] == expected["brand"]
    assert clear["class_type"] == expected["class_type"]
    assert clear["producer_name"] == expected["producer_name"]
    assert clear["producer_address"] == expected["producer_address"]

    abv = re.search(
        r"([\d.]+)% Alc\./Vol\. \(([\d.]+) Proof\)", clear["alcohol_content"]
    )
    assert abv is not None
    expected_abv = Decimal(expected["alcohol_content"]["measurement"]["value"])
    assert Decimal(abv[1]) == expected_abv
    assert Decimal(abv[2]) == expected_abv * 2
    volume = re.fullmatch(r"([\d.]+) mL", clear["net_contents"])
    assert volume is not None
    assert Decimal(volume[1]) == Decimal(
        expected["net_contents"]["measurement"]["value"]
    )
    assert expected["net_contents"]["measurement"]["unit"] == "ml"
    assert clear["country_of_origin"] is None
    assert not expected["is_imported"]

    for name in ("labels/starter-clear.png", "labels/starter-warning-changed.png"):
        style = STARTERS[name]["visible_style"]
        assert style == {
            "warning_heading": "bold, uppercase",
            "warning_body": "regular weight",
        }
        assert (
            STARTERS[name]["visible_text"]["warning_heading"] == "GOVERNMENT WARNING:"
        )
    title_case = STARTERS["labels/starter-warning-title-case.png"]
    assert title_case["visible_text"]["warning_heading"] == "Government Warning:"
    assert title_case["visible_style"] == {
        "warning_heading": "bold, title case",
        "warning_body": "regular weight",
    }
    outcomes = SCENARIOS["S01-clear-match"]["expected_outcomes"]
    for check in (
        "warning_heading_case",
        "warning_heading_bold",
        "warning_body_not_bold",
    ):
        assert outcomes[check] == "match"

    assert {k for k in clear if clear[k] != changed[k]} == {"warning_body"}
    assert (
        clear["warning_body"].replace("impairs", "affects") == changed["warning_body"]
    )
    assert STARTERS["labels/starter-clear.png"]["provenance"]["defect"] is None


@pytest.mark.parametrize(
    ("scenario_id", "image_file", "heading_style", "body_style", "heading", "body"),
    [
        (
            "S01-clear-match",
            "labels/starter-clear.png",
            "bold, uppercase",
            "regular weight",
            "match",
            "match",
        ),
        (
            "S17-warning-heading-not-bold",
            "labels/warning-heading-regular.png",
            "regular weight, uppercase",
            "regular weight",
            "discrepancy",
            "match",
        ),
        (
            "S18-warning-all-bold",
            "labels/warning-all-bold.png",
            "bold, uppercase",
            "bold",
            "match",
            "discrepancy",
        ),
    ],
)
def test_font_weight_fixtures_pair_annotated_style_with_expected_outcomes(
    scenario_id, image_file, heading_style, body_style, heading, body
):
    scenario = SCENARIOS[scenario_id]
    entry = STARTERS[image_file]

    assert scenario["image_files"] == [image_file]
    assert entry["visible_style"] == {
        "warning_heading": heading_style,
        "warning_body": body_style,
    }
    outcomes = scenario["expected_outcomes"]
    assert outcomes["warning_heading_bold"] == heading
    assert outcomes["warning_body_not_bold"] == body
    assert outcomes["warning_wording"] == "match"
    assert outcomes["warning_heading_case"] == "match"


def test_font_weight_fixtures_differ_from_clear_only_in_warning_weight():
    clear = STARTERS["labels/starter-clear.png"]
    baseline = _application("S01-clear-match")

    for scenario_id, image_file in (
        ("S17-warning-heading-not-bold", "labels/warning-heading-regular.png"),
        ("S18-warning-all-bold", "labels/warning-all-bold.png"),
    ):
        entry = STARTERS[image_file]
        assert entry["visible_text"] == clear["visible_text"]
        assert entry["provenance"]["defect"]
        assert SCENARIOS[scenario_id]["deliberate_defect"]
        assert _differences(baseline, _application(scenario_id)) == {
            "application_id",
            "images",
        }


def _extracted(field_id: FieldId, text: str | None) -> ExtractedField:
    if text is None:
        return ExtractedField(
            field_id, ExtractionState.MISSING, (), "Not printed on the label."
        )
    return ExtractedField(
        field_id, ExtractionState.OBSERVED, (Observation(text, "front"),)
    )


@pytest.mark.parametrize(
    ("image_file", "expected_wording", "expected_heading_case"),
    [
        ("labels/starter-clear.png", CheckOutcome.MATCH, CheckOutcome.MATCH),
        (
            "labels/starter-warning-changed.png",
            CheckOutcome.DISCREPANCY,
            CheckOutcome.MATCH,
        ),
        (
            "labels/starter-warning-title-case.png",
            CheckOutcome.DISCREPANCY,
            CheckOutcome.DISCREPANCY,
        ),
    ],
)
def test_warning_text_checks_match_starter_annotations(
    image_file, expected_wording, expected_heading_case
):
    image = STARTERS[image_file]["visible_text"]
    warning = f"{image['warning_heading']} {image['warning_body']}"
    extracted = _extracted(FieldId.WARNING_TEXT, warning)

    assert compare_warning_wording(extracted).outcome is expected_wording
    assert compare_warning_heading_case(extracted).outcome is expected_heading_case


@pytest.mark.parametrize(
    "scenario", SIMPLE_SCENARIOS.values(), ids=SIMPLE_SCENARIOS.keys()
)
def test_annotated_label_text_yields_the_expected_field_outcomes(scenario):
    """Offline check of the comparison rules against annotated pixels, not extraction."""
    application = application_from_dict(scenario["application"])
    image = STARTERS[scenario["image_files"][0]]["visible_text"]

    def field(field_id: FieldId) -> ExtractedField:
        return _extracted(field_id, image[field_id.value])

    warning = _extracted(
        FieldId.WARNING_TEXT, f"{image['warning_heading']} {image['warning_body']}"
    )

    results = {
        CheckId.BRAND: compare_brand(application.brand, field(FieldId.BRAND)),
        CheckId.CLASS_TYPE: compare_class_type(
            application.class_type, field(FieldId.CLASS_TYPE)
        ),
        CheckId.ALCOHOL_CONTENT: compare_alcohol_content(
            application.alcohol_content, field(FieldId.ALCOHOL_CONTENT)
        ),
        CheckId.NET_CONTENTS: compare_net_contents(
            application.net_contents, field(FieldId.NET_CONTENTS)
        ),
        CheckId.PRODUCER_NAME: compare_producer_name(
            application.producer_name, field(FieldId.PRODUCER_NAME)
        ),
        CheckId.PRODUCER_ADDRESS: compare_producer_address(
            application.producer_address, field(FieldId.PRODUCER_ADDRESS)
        ),
        CheckId.WARNING_WORDING: compare_warning_wording(warning),
        CheckId.WARNING_HEADING_CASE: compare_warning_heading_case(warning),
        CheckId.COUNTRY_OF_ORIGIN: compare_country_of_origin(
            application.country_of_origin,
            field(FieldId.COUNTRY_OF_ORIGIN),
            application.is_imported,
        ),
    }
    expected = scenario["expected_outcomes"]
    assert {c.value: r.outcome.value for c, r in results.items()} == {
        c.value: expected[c.value] for c in results
    }


@pytest.mark.parametrize(
    "scenario", SIMPLE_SCENARIOS.values(), ids=SIMPLE_SCENARIOS.keys()
)
def test_review_of_annotated_label_text_matches_expected_field_outcomes(scenario):
    from alcohol_label.review import review_after_extraction

    application = application_from_dict(scenario["application"])
    image = STARTERS[scenario["image_files"][0]]["visible_text"]
    fields = tuple(_extracted(f, image[f.value]) for f in FieldId if f.value in image)
    if "warning_heading" in image and "warning_body" in image:
        fields += (
            _extracted(
                FieldId.WARNING_TEXT,
                f"{image['warning_heading']} {image['warning_body']}",
            ),
        )

    response = review_after_extraction(application, (), fields)

    got = {r.check_id.value: r.outcome.value for r in response.check_results}
    expected = scenario["expected_outcomes"]
    comparable = {
        c for c in got if c not in {"warning_heading_bold", "warning_body_not_bold"}
    }
    assert {c: got[c] for c in comparable} == {c: expected[c] for c in comparable}
    assert not response.all_clear


@pytest.mark.parametrize(
    "scenario_id",
    ["S01-clear-match", "S17-warning-heading-not-bold", "S18-warning-all-bold"],
)
def test_style_comparators_reproduce_annotated_font_weight_outcomes(scenario_id):
    """Offline: annotated pixels fed through the comparators, not live extraction."""
    scenario = SCENARIOS[scenario_id]
    entry = STARTERS[scenario["image_files"][0]]

    def judged(text: str) -> StyleJudgement:
        return (
            StyleJudgement.BOLD if text.startswith("bold") else StyleJudgement.NOT_BOLD
        )

    style = WarningStyleObservation(
        "front",
        judged(entry["visible_style"]["warning_heading"]),
        judged(entry["visible_style"]["warning_body"]),
    )
    text = entry["visible_text"]
    warning = _extracted(
        FieldId.WARNING_TEXT, f"{text['warning_heading']} {text['warning_body']}"
    )

    heading = compare_warning_heading_bold((style,), warning)
    body = compare_warning_body_not_bold((style,), warning)

    expected = scenario["expected_outcomes"]
    assert heading.outcome.value == expected["warning_heading_bold"]
    assert body.outcome.value == expected["warning_body_not_bold"]


def test_illegible_fields_name_real_fields_and_only_appear_on_known_images():
    valid = {f.value for f in FieldId}
    for entry in STARTERS.values():
        assert set(entry.get("illegible_fields", [])) <= valid, entry["file"]


def test_expected_outcomes_follow_the_legibility_and_absence_annotations():
    """Unreadable or unprinted evidence is never expected to be a match."""
    for sid, scenario in SCENARIOS.items():
        outcomes = scenario["expected_outcomes"]
        for image in _images_of(scenario):
            if "alcohol_content" in image.get("illegible_fields", []):
                assert outcomes["alcohol_content"] == "needs_review", sid
        warning_unreadable = all(
            "warning_text" in image.get("illegible_fields", [])
            or image["visible_text"]["warning_heading"] is None
            for image in _images_of(scenario)
        )
        if warning_unreadable:
            for check in _WARNING_CHECKS:
                assert outcomes[check] == "needs_review", (sid, check)


def test_front_back_scenarios_split_the_statements_across_two_images():
    both = SCENARIOS["S19-front-back-warning-on-back"]
    front, back = _images_of(both)

    assert both["image_files"] == [
        "labels/front-no-warning.png",
        "labels/back-warning-only.png",
    ]
    assert front["visible_text"]["warning_heading"] is None
    assert front["visible_text"]["brand"] == "OLD TOM"
    assert back["visible_text"]["brand"] is None
    assert back["visible_text"]["warning_heading"] == "GOVERNMENT WARNING:"
    assert set(both["expected_outcomes"].values()) == {"match", "not_applicable"}

    conflict = SCENARIOS["S20-front-back-warning-conflict"]
    one, other = _images_of(conflict)
    assert {
        k
        for k in one["visible_text"]
        if one["visible_text"][k] != other["visible_text"][k]
    } == {"warning_body"}
    assert conflict["expected_outcomes"]["warning_wording"] == "needs_review"
    assert conflict["expected_outcomes"]["brand"] == "match"


def _covers(predicate) -> list[str]:
    return [sid for sid, s in SCENARIOS.items() if predicate(s)]


def _discrepant(check: str):
    return lambda s: s["expected_outcomes"][check] == "discrepancy"


def test_scenarios_cover_every_regression_category_in_the_acceptance_criteria():
    def all_clear(s):
        return set(s["expected_outcomes"].values()) <= {"match", "not_applicable"}

    def brand_case_only(s):
        brand = s["application"]["brand"]
        shown = _images_of(s)[0]["visible_text"]["brand"]
        return brand != shown and brand.casefold() == shown.casefold()

    def volume_equivalence(s):
        net = s["application"]["net_contents"]["measurement"]
        return net["unit"] != "ml" and s["expected_outcomes"]["net_contents"] == "match"

    categories = {
        "clear match": _covers(lambda s: all_clear(s) and len(s["image_files"]) == 1),
        "brand case": _covers(brand_case_only),
        "numeric mismatch": _covers(_discrepant("alcohol_content")),
        "volume equivalence": _covers(volume_equivalence),
        "warning text": _covers(_discrepant("warning_wording")),
        "warning case": _covers(_discrepant("warning_heading_case")),
        "warning style": _covers(_discrepant("warning_heading_bold"))
        + _covers(_discrepant("warning_body_not_bold")),
        "front/back evidence": _covers(lambda s: len(s["image_files"]) == 2),
        "processing failure": _covers(lambda s: "provider_failure" in s),
        "unknown evidence": _covers(
            lambda s: "needs_review" in s["expected_outcomes"].values()
        ),
    }

    assert len(SCENARIOS) >= 10
    assert {name: ids for name, ids in categories.items() if not ids} == {}
    assert len(categories["front/back evidence"]) >= 2


def test_provider_failure_scenarios_expect_an_error_and_no_finding():
    failing = {sid: s for sid, s in SCENARIOS.items() if "provider_failure" in s}
    codes = {code.value for code in ErrorCode}
    kinds = {"timeout", "rate_limited", "endpoint_blocked", "invalid_response"}

    assert len(failing) >= 3
    for sid, scenario in failing.items():
        failure = scenario["provider_failure"]
        image_ids = {i["image_id"] for i in scenario["application"]["images"]}
        assert failure["kind"] in kinds, sid
        assert failure["image"] in image_ids, sid
        assert failure["expected_code"] in codes, sid
        assert set(scenario["expected_outcomes"].values()) == {
            "not_evaluated",
            "not_applicable",
        }, sid
    assert {s["provider_failure"]["kind"] for s in failing.values()} == kinds
