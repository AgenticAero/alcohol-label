"""Field comparison rules; currently the brand check only."""

import re
import unicodedata

from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    CheckResult,
    EvidenceRef,
    ExtractedField,
    ExtractionState,
    FieldId,
)

_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'"})


def normalize_brand(text: str) -> str:
    """Unicode (NFKC), typographic apostrophes, whitespace and case; keeps punctuation."""
    text = unicodedata.normalize("NFKC", text).translate(_APOSTROPHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def compare_brand(
    expected: str | None, extracted: ExtractedField | None
) -> CheckResult:
    """Compare the expected brand with the extracted brand; never fuzzy-match."""
    if expected is None:
        return _result(
            CheckOutcome.NOT_EVALUATED,
            None,
            extracted,
            "Expected brand was not supplied.",
        )
    if extracted is None:
        return _result(
            CheckOutcome.NEEDS_REVIEW,
            expected,
            None,
            "No brand was extracted from the label images.",
        )
    if extracted.state is not ExtractionState.OBSERVED:
        return _result(
            CheckOutcome.NEEDS_REVIEW,
            expected,
            extracted,
            f"Brand extraction is {extracted.state.value}: {extracted.explanation}",
        )
    observed = extracted.observations[0].raw_text
    if normalize_brand(expected) == normalize_brand(observed):
        note = (
            None
            if expected == observed
            else "Matches after case, whitespace and apostrophe normalization."
        )
        return _result(CheckOutcome.MATCH, expected, extracted, note)
    return _result(
        CheckOutcome.DISCREPANCY,
        expected,
        extracted,
        "Label brand differs from the expected brand after normalization.",
    )


def _result(
    outcome: CheckOutcome,
    expected: str | None,
    extracted: ExtractedField | None,
    explanation: str | None,
) -> CheckResult:
    observations = extracted.observations if extracted else ()
    observed = " | ".join(dict.fromkeys(o.raw_text for o in observations)) or None
    evidence = tuple(
        EvidenceRef(FieldId.BRAND, index, o.image_id)
        for index, o in enumerate(observations)
    )
    return CheckResult(
        check_id=CheckId.BRAND,
        outcome=outcome,
        field_id=FieldId.BRAND,
        expected_value=expected,
        observed_value=observed,
        explanation=explanation,
        evidence=evidence,
    )
