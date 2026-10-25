import pytest

from alcohol_label.presentation import (
    check_label,
    evidence_actions,
    evidence_names,
    failure_guidance,
    image_names,
    input_error_actions,
    missing_values_note,
    summarize,
)
from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    CheckResult,
    ErrorCode,
    EvidenceRef,
    ExtractedField,
    ExtractionState,
    FieldId,
    ImageReference,
    Observation,
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


def test_image_names_show_file_names_and_add_the_id_only_when_names_repeat():
    distinct = (
        ImageReference("image-1", "front.png"),
        ImageReference("image-2", "b.jpg"),
    )
    repeated = (
        ImageReference("image-1", "label.png"),
        ImageReference("image-2", "label.png"),
    )

    assert image_names(distinct) == {"image-1": "front.png", "image-2": "b.jpg"}
    assert image_names(repeated) == {
        "image-1": "label.png (image-1)",
        "image-2": "label.png (image-2)",
    }


def test_evidence_names_list_distinct_images_in_order_by_file_name():
    names = {"image-1": "front.png", "image-2": "back.png"}
    result = CheckResult(
        CheckId.BRAND,
        CheckOutcome.DISCREPANCY,
        FieldId.BRAND,
        explanation="Differs.",
        evidence=(
            EvidenceRef(FieldId.BRAND, 0, "image-2"),
            EvidenceRef(FieldId.BRAND, 1, "image-1"),
            EvidenceRef(FieldId.BRAND, 2, "image-2"),
        ),
    )
    unresolved = _result(CheckId.CLASS_TYPE, CheckOutcome.NEEDS_REVIEW)

    assert evidence_names(result, names) == "back.png, front.png"
    assert evidence_names(unresolved, names) == ""
    assert evidence_names(result, {}) == "image-2, image-1"


def _field_state(field_id, state):
    if state is ExtractionState.OBSERVED:
        return ExtractedField(field_id, state, (Observation("x", "image-1"),))
    if state is ExtractionState.CONFLICTING:
        both = (Observation("a", "image-1"), Observation("b", "image-2"))
        return ExtractedField(field_id, state, both, "Reason.")
    return ExtractedField(field_id, state, (), "Reason.")


def test_missing_evidence_asks_for_an_image_showing_it():
    response = _response({CheckId.NET_CONTENTS: CheckOutcome.NEEDS_REVIEW})
    fields = (_field_state(FieldId.NET_CONTENTS, ExtractionState.MISSING),)

    (action,) = evidence_actions(response, fields)

    assert "net contents was not found" in action
    assert "Upload an image that shows it" in action
    assert evidence_actions(response, ()) == (action,)


def test_uncertain_evidence_asks_for_a_clearer_image():
    response = _response({CheckId.BRAND: CheckOutcome.NEEDS_REVIEW})
    fields = (_field_state(FieldId.BRAND, ExtractionState.UNCERTAIN),)

    (action,) = evidence_actions(response, fields)

    assert "could not be read reliably" in action
    assert "clearer, closer image" in action


def test_conflicting_evidence_says_images_disagree():
    response = _response({CheckId.BRAND: CheckOutcome.NEEDS_REVIEW})
    fields = (_field_state(FieldId.BRAND, ExtractionState.CONFLICTING),)

    (action,) = evidence_actions(response, fields)

    assert "different readings of the brand" in action


def test_warning_checks_share_one_action_per_reason():
    response = _response(
        {
            CheckId.WARNING_WORDING: CheckOutcome.NEEDS_REVIEW,
            CheckId.WARNING_HEADING_CASE: CheckOutcome.NEEDS_REVIEW,
        }
    )
    fields = (_field_state(FieldId.WARNING_TEXT, ExtractionState.MISSING),)

    actions = evidence_actions(response, fields)

    assert len(actions) == 1
    assert "government warning was not found" in actions[0]


def test_observed_warning_with_unclear_weight_points_to_the_original_image():
    response = _response(
        {
            CheckId.WARNING_HEADING_BOLD: CheckOutcome.NEEDS_REVIEW,
            CheckId.WARNING_BODY_NOT_BOLD: CheckOutcome.NEEDS_REVIEW,
        }
    )
    fields = (_field_state(FieldId.WARNING_TEXT, ExtractionState.OBSERVED),)

    (action,) = evidence_actions(response, fields)

    assert "font weight could not be judged" in action
    assert "sharper image" in action


def test_ambiguous_observed_value_asks_for_manual_check_and_other_outcomes_add_nothing():
    response = _response(
        {
            CheckId.ALCOHOL_CONTENT: CheckOutcome.NEEDS_REVIEW,
            CheckId.BRAND: CheckOutcome.DISCREPANCY,
            CheckId.CLASS_TYPE: CheckOutcome.NOT_EVALUATED,
        }
    )
    fields = (_field_state(FieldId.ALCOHOL_CONTENT, ExtractionState.OBSERVED),)

    (action,) = evidence_actions(response, fields)

    assert "alcohol content" in action and "yourself" in action


def test_clean_review_has_no_evidence_actions():
    assert evidence_actions(_response(), ()) == ()


def _failure(code, retryable):
    return ProcessingError(ProcessingStage.EXTRACTION, code, "Message.", retryable)


def test_retryable_failure_offers_retry_and_says_inputs_are_kept():
    guidance = failure_guidance((_failure(ErrorCode.PROVIDER_TIMEOUT, True),))

    assert guidance.can_retry
    assert "took too long" in guidance.lines[0]
    assert "Your entries and images are kept" in guidance.lines[-1]


def test_non_retryable_failure_says_retry_will_not_help_and_offers_no_retry():
    guidance = failure_guidance((_failure(ErrorCode.INTERNAL_ERROR, False),))

    assert not guidance.can_retry
    assert "retrying will not fix this" in guidance.lines[0]
    assert all("Retry" not in line for line in guidance.lines)


def test_mixed_failures_can_retry_and_repeat_codes_are_listed_once():
    guidance = failure_guidance(
        (
            _failure(ErrorCode.RATE_LIMITED, True),
            _failure(ErrorCode.RATE_LIMITED, True),
            _failure(ErrorCode.INTERNAL_ERROR, False),
        )
    )

    assert guidance.can_retry
    assert len(guidance.lines) == 3


def test_failure_guidance_exposes_no_provider_detail():
    text = " ".join(
        line
        for code in ErrorCode
        for line in failure_guidance((_failure(code, True),)).lines
    ).lower()

    for word in ("http", "openai", "api key", "api_key", "token", "traceback"):
        assert word not in text


def test_no_failures_gives_no_guidance():
    assert failure_guidance(()).lines == ()
    assert not failure_guidance(()).can_retry


def test_input_errors_say_what_to_fix():
    lines = input_error_actions(
        (
            "Application ID is required.",
            "Alcohol content must be a number.",
            "Net contents must be greater than zero.",
            "Upload at least one label image.",
            "Upload at most 2 label images.",
            "front.png: file is not a readable image.",
        )
    )

    assert lines == (
        "Application ID is required. Enter it, then click Verify.",
        "Alcohol content must be a number. Correct the value, then click Verify.",
        "Net contents must be greater than zero. Correct the value, then click Verify.",
        "Upload at least one label image. Choose a label image, then click Verify.",
        "Upload at most 2 label images. Remove the extra images, then click Verify.",
        "front.png: file is not a readable image. Replace or remove that file, then click Verify.",
    )


def test_missing_expected_values_are_a_note_not_an_error():
    note = missing_values_note((FieldId.BRAND, FieldId.CLASS_TYPE))

    assert "brand, class type" in note
    assert "not evaluated" in note
    assert missing_values_note(()) is None
