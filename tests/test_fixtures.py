import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

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
)
from alcohol_label.schemas import (
    ApplicationData,
    CheckId,
    CheckOutcome,
    ExtractedField,
    ExtractionState,
    FieldId,
    Observation,
    application_from_dict,
    application_to_dict,
)

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
SCENARIOS = {s["scenario_id"]: s for s in MANIFEST["scenarios"]}
STARTERS = {i["file"]: i for i in MANIFEST["images"]}
REFERENCES = {i["file"]: i for i in MANIFEST["reference_images"]["images"]}


def _application(scenario_id: str) -> dict:
    return SCENARIOS[scenario_id]["application"]


def _differences(a: dict, b: dict) -> set[str]:
    return {key for key in a if a[key] != b[key]}


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


def test_starter_scenarios_cover_the_four_required_cases():
    baseline = _application("S01-clear-match")
    assert {
        "S01-clear-match",
        "S02-brand-case-only",
        "S03-abv-mismatch",
        "S04-warning-text-changed",
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


def _extracted(field_id: FieldId, text: str | None) -> ExtractedField:
    if text is None:
        return ExtractedField(
            field_id, ExtractionState.MISSING, (), "Not printed on the label."
        )
    return ExtractedField(
        field_id, ExtractionState.OBSERVED, (Observation(text, "front"),)
    )


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_annotated_label_text_yields_the_expected_field_outcomes(scenario):
    """Offline check of the comparison rules against annotated pixels, not extraction."""
    application = application_from_dict(scenario["application"])
    image = STARTERS[scenario["image_files"][0]]["visible_text"]

    def field(field_id: FieldId) -> ExtractedField:
        return _extracted(field_id, image[field_id.value])

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


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_review_of_annotated_label_text_matches_expected_field_outcomes(scenario):
    from alcohol_label.review import review_after_extraction

    application = application_from_dict(scenario["application"])
    image = STARTERS[scenario["image_files"][0]]["visible_text"]
    fields = tuple(_extracted(f, image[f.value]) for f in FieldId if f.value in image)

    response = review_after_extraction(application, (), fields)

    got = {r.check_id.value: r.outcome.value for r in response.check_results}
    expected = scenario["expected_outcomes"]
    comparable = {c for c in got if not c.startswith("warning_")}
    assert {c: got[c] for c in comparable} == {c: expected[c] for c in comparable}
    assert not response.all_clear
