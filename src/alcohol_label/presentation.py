"""Reviewer-facing summary of a review; no UI imports so it can be tested offline."""

from dataclasses import dataclass

from alcohol_label.schemas import CheckId, CheckOutcome, ReviewResponse

_OUTCOME_WORDS = {
    CheckOutcome.MATCH: "matched",
    CheckOutcome.DISCREPANCY: "discrepancy",
    CheckOutcome.NEEDS_REVIEW: "needs review",
    CheckOutcome.NOT_EVALUATED: "not evaluated",
    CheckOutcome.NOT_APPLICABLE: "not applicable",
}


def check_label(check_id: CheckId) -> str:
    return check_id.value.replace("_", " ")


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    """Counts for all five outcomes plus the named problems behind a not-a-pass.

    ``all_clear`` is taken from the response, never recomputed here, so the
    summary cannot report a pass the schema would not.
    """

    counts: dict[CheckOutcome, int]
    total: int
    discrepancies: tuple[CheckId, ...]
    needs_review: tuple[CheckId, ...]
    not_evaluated: tuple[CheckId, ...]
    processing_error_count: int
    all_clear: bool
    headline: str
    counts_text: str
    problems: tuple[str, ...]


def _names(check_ids: tuple[CheckId, ...]) -> str:
    return ", ".join(check_label(c) for c in check_ids)


def summarize(response: ReviewResponse) -> ReviewSummary:
    results = response.check_results
    counts = {o: sum(r.outcome is o for r in results) for o in CheckOutcome}

    def with_outcome(outcome: CheckOutcome) -> tuple[CheckId, ...]:
        return tuple(r.check_id for r in results if r.outcome is outcome)

    discrepancies = with_outcome(CheckOutcome.DISCREPANCY)
    needs_review = with_outcome(CheckOutcome.NEEDS_REVIEW)
    not_evaluated = with_outcome(CheckOutcome.NOT_EVALUATED)
    error_count = len(response.processing_errors)

    problems = []
    if discrepancies:
        problems.append(f"Discrepancies: {_names(discrepancies)}.")
    if needs_review:
        problems.append(f"Needs review: {_names(needs_review)}.")
    if not_evaluated:
        problems.append(f"Not evaluated: {_names(not_evaluated)}.")
    if error_count:
        problems.append(
            f"Processing failed ({error_count} error"
            f"{'s' if error_count != 1 else ''}); results may be incomplete."
        )
    if not response.all_clear and not problems:
        problems.append("Not every check has a result.")

    counts_text = (
        f"Of {len(results)} checks: "
        + ", ".join(f"{counts[o]} {_OUTCOME_WORDS[o]}" for o in _OUTCOME_WORDS)
        + "."
    )
    headline = (
        "Pass: all supported checks passed" if response.all_clear else "Not a pass"
    )
    return ReviewSummary(
        counts=counts,
        total=len(results),
        discrepancies=discrepancies,
        needs_review=needs_review,
        not_evaluated=not_evaluated,
        processing_error_count=error_count,
        all_clear=response.all_clear,
        headline=headline,
        counts_text=counts_text,
        problems=tuple(problems),
    )
