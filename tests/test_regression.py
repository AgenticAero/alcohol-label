"""Offline end-to-end regression over the annotated development scenarios.

A fake provider returns what a faithful model would say for each annotated
image (or fails as the scenario declares). The real ``extract_application`` and
``review_after_extraction`` then run unchanged and every outcome is compared
with the manifest. These tests validate parsing, aggregation and rules against
annotations. They say nothing about live extraction accuracy or hosted
performance; live runs are separate (scripts/al13_style_eval.py).
"""

import socket
import urllib.error
import urllib.request

import pytest

from alcohol_label import extraction
from alcohol_label.extraction import (
    ExtractionResult,
    ProviderConfig,
    extract_application,
)
from alcohol_label.review import review_after_extraction
from alcohol_label.schemas import (
    CheckOutcome,
    ExtractionState,
    ReviewResponse,
    ReviewStatus,
    application_from_dict,
)

from .support import FIXTURES, SCENARIOS, STARTERS, provider_response

DEVELOPMENT = {sid: s for sid, s in SCENARIOS.items() if s["split"] == "development"}
_TEST_CONFIG = ProviderConfig("test-key", "test-model")
_INVALID = {"output": [{"content": [{"type": "output_text", "text": "not json"}]}]}


def _raise_for(kind: str):
    if kind == "timeout":
        raise TimeoutError("timed out")
    if kind == "rate_limited":
        raise urllib.error.HTTPError("http://provider", 429, "Too Many", {}, None)
    if kind == "endpoint_blocked":
        raise urllib.error.URLError("blocked")
    return _INVALID


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Fail on any network use or credential lookup, so the suite is provably offline."""

    def forbidden(*args, **kwargs):
        raise AssertionError("regression tests must not use the network or credentials")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(ProviderConfig, "from_environment", forbidden)


def run_scenario(scenario: dict) -> tuple[ExtractionResult, ReviewResponse]:
    application = application_from_dict(scenario["application"])
    failure = scenario.get("provider_failure")
    responses, payloads = {}, []
    for reference, file in zip(
        application.images, scenario["image_files"], strict=True
    ):
        payload = f"{reference.image_id}:{file}".encode()
        payloads.append(payload)
        if failure and failure["image"] == reference.image_id:
            responses[payload] = failure["kind"]
        else:
            responses[payload] = provider_response(STARTERS[file])

    def fake_call(data, config):
        outcome = responses[data]
        return _raise_for(outcome) if isinstance(outcome, str) else outcome

    original = extraction._call_provider
    extraction._call_provider = fake_call
    try:
        result = extract_application(application.images, payloads, config=_TEST_CONFIG)
    finally:
        extraction._call_provider = original
    review = review_after_extraction(
        application, result.errors, result.fields, result.warning_styles
    )
    return result, review


def mismatches(scenario: dict, review: ReviewResponse) -> dict[str, tuple[str, str]]:
    got = {r.check_id.value: r.outcome.value for r in review.check_results}
    expected = scenario["expected_outcomes"]
    return {
        check: (want, got.get(check, "missing"))
        for check, want in expected.items()
        if got.get(check) != want
    }


@pytest.mark.parametrize("scenario", DEVELOPMENT.values(), ids=DEVELOPMENT.keys())
def test_every_development_scenario_matches_its_annotated_outcomes(scenario):
    _, review = run_scenario(scenario)

    assert mismatches(scenario, review) == {}, (
        f"{scenario['scenario_id']}: (expected, got) per check"
    )
    assert len(review.check_results) == len(scenario["expected_outcomes"])


def test_the_harness_reports_a_wrong_expectation_instead_of_passing_vacuously():
    scenario = dict(DEVELOPMENT["S01-clear-match"])
    scenario["expected_outcomes"] = {
        **scenario["expected_outcomes"],
        "brand": "discrepancy",
    }

    _, review = run_scenario(scenario)

    assert mismatches(scenario, review) == {"brand": ("discrepancy", "match")}


def test_front_back_scenarios_use_evidence_from_both_images():
    result, review = run_scenario(DEVELOPMENT["S19-front-back-warning-on-back"])

    warning = next(f for f in result.fields if f.field_id.value == "warning_text")
    assert [o.image_id for o in warning.observations] == ["back"]
    assert review.all_clear

    conflict_result, conflict = run_scenario(
        DEVELOPMENT["S20-front-back-warning-conflict"]
    )
    warning = next(
        f for f in conflict_result.fields if f.field_id.value == "warning_text"
    )
    assert warning.state is ExtractionState.CONFLICTING
    assert [o.image_id for o in warning.observations] == ["front", "back"]
    wording = next(
        r for r in conflict.check_results if r.check_id.value == "warning_wording"
    )
    assert [e.image_id for e in wording.evidence] == ["front", "back"]
    assert not conflict.all_clear


FAILING = {sid: s for sid, s in DEVELOPMENT.items() if "provider_failure" in s}


@pytest.mark.parametrize("scenario", FAILING.values(), ids=FAILING.keys())
def test_provider_failures_are_errors_kept_apart_from_check_outcomes(scenario):
    result, review = run_scenario(scenario)

    assert [e.code.value for e in review.processing_errors] == [
        scenario["provider_failure"]["expected_code"]
    ]
    assert review.status is ReviewStatus.INCOMPLETE
    assert not review.all_clear
    assert {r.outcome for r in review.check_results} <= {
        CheckOutcome.NOT_EVALUATED,
        CheckOutcome.NOT_APPLICABLE,
    }
    assert all(not r.evidence for r in review.check_results)
    assert tuple(review.processing_errors) == tuple(result.errors)


def test_a_failure_on_one_image_keeps_the_other_images_observations():
    scenario = DEVELOPMENT["S28-provider-failure-one-of-two-images"]

    result, review = run_scenario(scenario)

    brand = next(f for f in result.fields if f.field_id.value == "brand")
    assert [o.raw_text for o in brand.observations] == ["OLD TOM"]
    assert brand.state is ExtractionState.UNCERTAIN
    assert review.processing_errors and not review.all_clear


def test_regression_run_uses_only_committed_fixtures_and_no_credentials():
    for scenario in DEVELOPMENT.values():
        for file in scenario["image_files"]:
            assert (FIXTURES / file).is_file()

    with pytest.raises(AssertionError, match="network or credentials"):
        ProviderConfig.from_environment()
    with pytest.raises(AssertionError, match="network or credentials"):
        socket.create_connection(("example.com", 443))
