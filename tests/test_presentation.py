import pytest

from alcohol_label.presentation import check_label, summarize
from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    CheckResult,
    ErrorCode,
    EvidenceRef,
    FieldId,
    ProcessingError,
    ProcessingStage,
    ReviewResponse,
)


def _field(check: CheckId) -> FieldId:
    try:
        return FieldId(check.value)
    except ValueError:
        return FieldId.WARNING_TEXT


def _result(check: CheckId, outcome: CheckOutcome) -> CheckResult:
    field = _field(check)
    evidence = ()
    if outcome is CheckOutcome.DISCREPANCY:
        evidence = (EvidenceRef(field, 0, "image-1"),)
    return CheckResult(
        check, outcome, field, explanation=f"{outcome.value} reason.", evidence=evidence
    )


def _response(overrides=None, errors=(), omit=()):
    overrides = overrides or {}
    results = tuple(
        _result(
            c,
            overrides.get(
                c,
                CheckOutcome.NOT_APPLICABLE
                if c is CheckId.COUNTRY_OF_ORIGIN
                else CheckOutcome.MATCH,
            ),
        )
        for c in CheckId
        if c not in omit
    )
    return ReviewResponse("APP-1", results, tuple(errors))


def _error() -> ProcessingError:
    return ProcessingError(
        ProcessingStage.EXTRACTION, ErrorCode.PROVIDER_TIMEOUT, "Timed out.", True
    )


def test_all_clear_review_is_a_pass_with_no_problems_listed():
    summary = summarize(_response())

    assert summary.all_clear
    assert summary.headline.startswith("Pass")
    assert summary.problems == ()
    assert summary.counts[CheckOutcome.MATCH] == 10
    assert summary.counts[CheckOutcome.NOT_APPLICABLE] == 1
    assert summary.total == 11


def test_counts_cover_all_five_outcomes_and_stay_distinct():
    summary = summarize(
        _response(
            {
                CheckId.BRAND: CheckOutcome.DISCREPANCY,
                CheckId.CLASS_TYPE: CheckOutcome.NEEDS_REVIEW,
                CheckId.NET_CONTENTS: CheckOutcome.NOT_EVALUATED,
            }
        )
    )

    assert summary.counts == {
        CheckOutcome.MATCH: 7,
        CheckOutcome.DISCREPANCY: 1,
        CheckOutcome.NEEDS_REVIEW: 1,
        CheckOutcome.NOT_EVALUATED: 1,
        CheckOutcome.NOT_APPLICABLE: 1,
    }
    assert "1 not evaluated" in summary.counts_text
    assert "1 not applicable" in summary.counts_text
    assert "7 matched" in summary.counts_text


def test_known_problems_are_named_by_check():
    summary = summarize(
        _response(
            {
                CheckId.ALCOHOL_CONTENT: CheckOutcome.DISCREPANCY,
                CheckId.WARNING_HEADING_BOLD: CheckOutcome.NEEDS_REVIEW,
                CheckId.WARNING_BODY_NOT_BOLD: CheckOutcome.NEEDS_REVIEW,
                CheckId.PRODUCER_NAME: CheckOutcome.NOT_EVALUATED,
            }
        )
    )

    assert not summary.all_clear
    assert summary.headline == "Not a pass"
    assert summary.discrepancies == (CheckId.ALCOHOL_CONTENT,)
    assert summary.needs_review == (
        CheckId.WARNING_HEADING_BOLD,
        CheckId.WARNING_BODY_NOT_BOLD,
    )
    assert summary.not_evaluated == (CheckId.PRODUCER_NAME,)
    assert summary.problems == (
        "Discrepancies: alcohol content.",
        "Needs review: warning heading bold, warning body not bold.",
        "Not evaluated: producer name.",
    )


@pytest.mark.parametrize(
    "outcome", [CheckOutcome.NEEDS_REVIEW, CheckOutcome.NOT_EVALUATED]
)
def test_unresolved_check_alone_is_not_a_pass(outcome):
    summary = summarize(_response({CheckId.BRAND: outcome}))

    assert not summary.all_clear
    assert summary.headline == "Not a pass"
    assert summary.problems


def test_not_applicable_alone_does_not_block_a_pass_and_is_not_a_match():
    summary = summarize(_response())

    assert summary.counts[CheckOutcome.NOT_APPLICABLE] == 1
    assert summary.counts[CheckOutcome.MATCH] == 10
    assert summary.not_evaluated == ()


def test_processing_errors_block_a_pass_and_are_reported_separately():
    summary = summarize(_response(errors=(_error(),)))

    assert not summary.all_clear
    assert summary.processing_error_count == 1
    assert summary.problems == (
        "Processing failed (1 error); results may be incomplete.",
    )
    assert summary.counts[CheckOutcome.DISCREPANCY] == 0
    assert summary.discrepancies == ()


def test_error_count_is_pluralised():
    summary = summarize(_response(errors=(_error(), _error())))

    assert "2 errors" in summary.problems[0]


def test_incomplete_response_is_never_all_clear():
    summary = summarize(_response(omit=(CheckId.NET_CONTENTS,)))

    assert not summary.all_clear
    assert summary.headline == "Not a pass"
    assert summary.problems == ("Not every check has a result.",)
    assert summary.total == 10


def test_empty_response_is_not_a_pass():
    summary = summarize(ReviewResponse("APP-1"))

    assert not summary.all_clear
    assert summary.total == 0
    assert summary.problems == ("Not every check has a result.",)


def test_check_label_uses_plain_words():
    assert check_label(CheckId.WARNING_HEADING_BOLD) == "warning heading bold"
