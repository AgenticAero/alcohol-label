import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from alcohol_label.schemas import (
    ApplicationData,
    CheckId,
    CheckOutcome,
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
    assert set(SCENARIOS) == {
        "S01-clear-match",
        "S02-brand-case-only",
        "S03-abv-mismatch",
        "S04-warning-text-changed",
    }
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

    assert {k for k in clear if clear[k] != changed[k]} == {"warning_body"}
    assert (
        clear["warning_body"].replace("impairs", "affects") == changed["warning_body"]
    )
    assert STARTERS["labels/starter-clear.png"]["provenance"]["defect"] is None
