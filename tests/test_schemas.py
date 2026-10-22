from alcohol_label.schemas import CheckId, CheckOutcome, ExtractionState, FieldId


def test_outcome_and_state_values_match_contract():
    assert {o.value for o in CheckOutcome} == {
        "match",
        "discrepancy",
        "needs_review",
        "not_applicable",
        "not_evaluated",
    }
    assert {s.value for s in ExtractionState} == {
        "observed",
        "missing",
        "uncertain",
        "conflicting",
    }


def test_processing_failures_are_not_states_or_outcomes():
    labels = {o.value for o in CheckOutcome} | {s.value for s in ExtractionState}
    assert not labels & {"error", "timeout", "failed", "processing_error"}


def test_warning_checks_are_distinct_and_comparison_checks_mirror_fields():
    warning = {c for c in CheckId if c.value.startswith("warning_")}
    assert len(warning) == 4
    comparison = {c.value for c in CheckId} - {c.value for c in warning}
    assert comparison == {f.value for f in FieldId} - {"warning_text"}
