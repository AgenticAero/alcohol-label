# Copyright (c) 2026 John Michael Egan. All rights reserved.
# Hiring evaluation permitted under the LICENSE file at the repository root.
"""Reviewer-facing summary of a review; no UI imports so it can be tested offline."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    CheckResult,
    ErrorCode,
    ExtractedField,
    ExtractionState,
    FieldId,
    ImageReference,
    ProcessingError,
    ReviewResponse,
)

_OUTCOME_WORDS = {
    CheckOutcome.MATCH: "matched",
    CheckOutcome.DISCREPANCY: "discrepancy",
    CheckOutcome.NEEDS_REVIEW: "needs review",
    CheckOutcome.NOT_EVALUATED: "not evaluated",
    CheckOutcome.NOT_APPLICABLE: "not applicable",
}


def check_label(check_id: CheckId) -> str:
    return check_id.value.replace("_", " ")


def image_names(images: Sequence[ImageReference]) -> dict[str, str]:
    """Name shown per image ID: the file name, plus the ID when file names repeat."""
    repeats = Counter(image.uri for image in images)
    return {
        image.image_id: (
            image.uri if repeats[image.uri] == 1 else f"{image.uri} ({image.image_id})"
        )
        for image in images
    }


def evidence_names(result: CheckResult, names: Mapping[str, str]) -> str:
    """Distinct evidence images of a result, in order, by display name."""
    shown = (names.get(ref.image_id, ref.image_id) for ref in result.evidence)
    return ", ".join(dict.fromkeys(shown))


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


_STYLE_CHECKS = frozenset({CheckId.WARNING_HEADING_BOLD, CheckId.WARNING_BODY_NOT_BOLD})


def _field_name(field_id: FieldId) -> str:
    if field_id is FieldId.WARNING_TEXT:
        return "government warning"
    return field_id.value.replace("_", " ")


def evidence_actions(
    response: ReviewResponse, fields: Sequence[ExtractedField]
) -> tuple[str, ...]:
    """What to do about each check that needs review, from how its field was read."""
    states = {f.field_id: f.state for f in fields}
    actions: list[str] = []
    for result in response.check_results:
        if result.outcome is not CheckOutcome.NEEDS_REVIEW or result.field_id is None:
            continue
        name = _field_name(result.field_id)
        state = states.get(result.field_id)
        if state is None or state is ExtractionState.MISSING:
            action = (
                f"The {name} was not found in the supplied images. Upload an "
                "image that shows it, such as the other side of the label."
            )
        elif state is ExtractionState.UNCERTAIN:
            action = (
                f"The {name} could not be read reliably. Upload a clearer, "
                "closer image of it."
            )
        elif state is ExtractionState.CONFLICTING:
            action = (
                f"The images show different readings of the {name}. Upload "
                "only the image of the label being reviewed, or compare the "
                "originals yourself."
            )
        elif result.check_id in _STYLE_CHECKS:
            action = (
                "The warning font weight could not be judged. Compare the "
                "original image yourself, or upload a sharper image of the "
                "warning."
            )
        else:
            action = (
                f"Check the {check_label(result.check_id)} in the original "
                "image yourself; the label text was ambiguous. See the reason "
                "in the results."
            )
        if action not in actions:
            actions.append(action)
    return tuple(actions)


_RETRY_NOTE = "Your entries and images are kept; use Retry to run Verify again."
_FAILURE_ACTIONS = {
    ErrorCode.RATE_LIMITED: "The extraction service is busy. Wait a moment, then retry.",
    ErrorCode.PROVIDER_TIMEOUT: "The extraction service took too long to answer.",
    ErrorCode.ENDPOINT_BLOCKED: (
        "The extraction service could not be reached. Check the network connection."
    ),
    ErrorCode.INVALID_PROVIDER_RESPONSE: (
        "The extraction service gave an unusable answer. Click Verify again; "
        "if it repeats, report it with the application ID."
    ),
    ErrorCode.IMAGE_UNREADABLE: (
        "An image could not be read. Replace it with a clearer JPEG or PNG, "
        "then click Verify."
    ),
    ErrorCode.INTERNAL_ERROR: (
        "Verification could not run, and retrying will not fix this. Ask an "
        "administrator to check the extraction service settings."
    ),
}


@dataclass(frozen=True, slots=True)
class FailureGuidance:
    lines: tuple[str, ...]
    can_retry: bool


def failure_guidance(errors: Sequence[ProcessingError]) -> FailureGuidance:
    """Next steps for processing failures; names no provider, URL or credential."""
    if not errors:
        return FailureGuidance((), False)
    lines = list(dict.fromkeys(_FAILURE_ACTIONS[e.code] for e in errors))
    can_retry = any(e.retryable for e in errors)
    if can_retry:
        lines.append(_RETRY_NOTE)
    return FailureGuidance(tuple(lines), can_retry)


def missing_values_note(missing_fields: Sequence[FieldId]) -> str | None:
    """Missing expected values do not block Verify; those checks stay not evaluated."""
    if not missing_fields:
        return None
    names = ", ".join(_field_name(f) for f in missing_fields)
    return (
        f"Expected values not entered: {names}. Enter them to run those "
        "checks; until then they are not evaluated."
    )


def input_error_actions(errors: Sequence[str]) -> tuple[str, ...]:
    """Each input problem followed by what to fix."""
    lines = []
    for error in errors:
        if error.endswith("is required."):
            fix = "Enter it, then click Verify."
        elif error.startswith("Upload at least"):
            fix = "Choose a label image, then click Verify."
        elif error.startswith("Upload at most"):
            fix = "Remove the extra images, then click Verify."
        elif "number" in error or "greater than zero" in error:
            fix = "Correct the value, then click Verify."
        else:
            fix = "Replace or remove that file, then click Verify."
        lines.append(f"{error} {fix}")
    return tuple(lines)


# Status text colours on the theme background; tests keep them above WCAG AA.
STATUS_COLORS = {
    "match": "#1B5E20",
    "discrepancy": "#B71C1C",
    "needs review": "#8A4B00",
    "not evaluated": "#595959",
    "not applicable": "#595959",
}


def _channel(value: int) -> float:
    s = value / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2 contrast ratio of two #RRGGBB colours, from 1 to 21."""
    lighter, darker = sorted((_luminance(foreground), _luminance(background)))[::-1]
    return (lighter + 0.05) / (darker + 0.05)
