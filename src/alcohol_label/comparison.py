"""Field comparison rules; brand today, built on helpers shared by all fields."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from alcohol_label.schemas import (
    CheckId,
    CheckOutcome,
    CheckResult,
    EvidenceRef,
    ExtractedField,
    ExtractionState,
    FieldId,
    Measurement,
    Unit,
)

_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'"})


def normalize_brand(text: str) -> str:
    """Unicode (NFKC), typographic apostrophes, whitespace and case; keeps punctuation."""
    text = unicodedata.normalize("NFKC", text).translate(_APOSTROPHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _field_name(check_id: CheckId) -> str:
    return check_id.value.replace("_", " ")


def unresolved_result(
    check_id: CheckId,
    expected: str | Measurement | None,
    extracted: ExtractedField | None,
) -> CheckResult | None:
    """Result when no comparison can run; None when the extraction is observed."""
    name = _field_name(check_id)
    if expected is None:
        return build_result(
            check_id,
            CheckOutcome.NOT_EVALUATED,
            None,
            extracted,
            f"Expected {name} was not supplied.",
        )
    if extracted is None:
        return build_result(
            check_id,
            CheckOutcome.NEEDS_REVIEW,
            expected,
            None,
            f"No {name} was extracted from the label images.",
        )
    if extracted.state is not ExtractionState.OBSERVED:
        return build_result(
            check_id,
            CheckOutcome.NEEDS_REVIEW,
            expected,
            extracted,
            f"{name.capitalize()} extraction is {extracted.state.value}: "
            f"{extracted.explanation}",
        )
    return None


def compare_text(
    check_id: CheckId, expected: str | None, extracted: ExtractedField | None
) -> CheckResult:
    """Compare a text field after brand-style normalization; never fuzzy-match."""
    unresolved = unresolved_result(check_id, expected, extracted)
    if unresolved is not None:
        return unresolved
    name = _field_name(check_id)
    observed = extracted.observations[0].raw_text
    if normalize_brand(expected) == normalize_brand(observed):
        note = (
            None
            if expected == observed
            else "Matches after case, whitespace and apostrophe normalization."
        )
        return build_result(check_id, CheckOutcome.MATCH, expected, extracted, note)
    return build_result(
        check_id,
        CheckOutcome.DISCREPANCY,
        expected,
        extracted,
        f"Label {name} differs from the expected {name} after normalization.",
    )


def compare_brand(
    expected: str | None, extracted: ExtractedField | None
) -> CheckResult:
    return compare_text(CheckId.BRAND, expected, extracted)


def compare_class_type(
    expected: str | None, extracted: ExtractedField | None
) -> CheckResult:
    return compare_text(CheckId.CLASS_TYPE, expected, extracted)


def compare_producer_name(
    expected: str | None, extracted: ExtractedField | None
) -> CheckResult:
    return compare_text(CheckId.PRODUCER_NAME, expected, extracted)


_PERCENT = re.compile(r"(\d+(?:\.\d+)?|\.\d+)\s*(?:%|percent\b)", re.IGNORECASE)
_PROOF = re.compile(r"\bproof\b", re.IGNORECASE)


def parse_percentages(text: str) -> tuple[Decimal, ...]:
    """Distinct percentage figures printed in ``text``, in order of appearance."""
    return tuple(dict.fromkeys(Decimal(m.group(1)) for m in _PERCENT.finditer(text)))


def compare_alcohol_content(
    expected: Measurement | None, extracted: ExtractedField | None
) -> CheckResult:
    """Compare expected ABV with the printed percentage; proof never substitutes."""
    check = CheckId.ALCOHOL_CONTENT
    unresolved = unresolved_result(check, expected, extracted)
    if unresolved is not None:
        return unresolved
    assert expected.unit is Unit.PERCENT_ABV
    raw = extracted.observations[0].raw_text
    values = parse_percentages(raw)
    if not values:
        reason = (
            "Label gives proof but no percentage; proof is not used as the ABV."
            if _PROOF.search(raw)
            else "No percentage could be read from the label text."
        )
        return build_result(
            check, CheckOutcome.NEEDS_REVIEW, expected, extracted, reason
        )
    if len(values) > 1:
        listed = ", ".join(f"{v}%" for v in values)
        return build_result(
            check,
            CheckOutcome.NEEDS_REVIEW,
            expected,
            extracted,
            f"Label text contains differing percentages ({listed}).",
        )
    if values[0] == expected.value:
        return build_result(
            check,
            CheckOutcome.MATCH,
            expected,
            extracted,
            f"Printed {values[0]}% equals the expected {expected.value}%.",
        )
    return build_result(
        check,
        CheckOutcome.DISCREPANCY,
        expected,
        extracted,
        f"Label states {values[0]}%; expected {expected.value}%.",
    )


_ML_PER_UNIT = {
    Unit.MILLILITER: Decimal(1),
    Unit.LITER: Decimal(1000),
    Unit.FLUID_OUNCE: Decimal("29.5735295625"),
}
_VOLUME = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?|\.\d+)\s*"
    r"(?:(?P<floz>fl\.?\s*oz|fluid\s+ounces?)"
    r"|(?P<ml>m\.?l|milli(?:l|li)?ters?)"
    r"|(?P<l>l|li(?:t|tr)?ers?|litres?))"
    r"(?![a-z])",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PrintedVolume:
    """One volume statement as printed, with its exact value in millilitres."""

    value: Decimal
    unit: Unit

    @property
    def millilitres(self) -> Decimal:
        return self.value * _ML_PER_UNIT[self.unit]

    @property
    def is_metric(self) -> bool:
        return self.unit is not Unit.FLUID_OUNCE


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _describe(value: Decimal, unit: Unit) -> str:
    return f"{_fmt(value)} {unit.value}"


def parse_volumes(text: str) -> tuple[PrintedVolume, ...]:
    """Supported volume statements (mL, L, fl oz) in order of appearance."""
    found = []
    for m in _VOLUME.finditer(text):
        unit = (
            Unit.FLUID_OUNCE
            if m.group("floz")
            else Unit.MILLILITER
            if m.group("ml")
            else Unit.LITER
        )
        found.append(PrintedVolume(Decimal(m.group(1)), unit))
    return tuple(found)


def compare_net_contents(
    expected: Measurement | None, extracted: ExtractedField | None
) -> CheckResult:
    """Compare against the printed metric statement; fl oz never decides the result."""
    check = CheckId.NET_CONTENTS
    unresolved = unresolved_result(check, expected, extracted)
    if unresolved is not None:
        return unresolved
    volumes = parse_volumes(extracted.observations[0].raw_text)
    metric = [v for v in volumes if v.is_metric]
    if not metric:
        reason = (
            "Only a fluid-ounce statement was observed; the required metric "
            "statement was not."
            if volumes
            else "No supported volume statement (mL, L or fl oz) could be read."
        )
        return build_result(
            check, CheckOutcome.NEEDS_REVIEW, expected, extracted, reason
        )
    distinct = {v.millilitres for v in metric}
    if len(distinct) > 1:
        listed = ", ".join(_describe(v.value, v.unit) for v in metric)
        return build_result(
            check,
            CheckOutcome.NEEDS_REVIEW,
            expected,
            extracted,
            f"Label text contains differing metric volumes ({listed}).",
        )
    printed = _describe(metric[0].value, metric[0].unit)
    wanted = _describe(expected.value, expected.unit)
    if distinct == {expected.value * _ML_PER_UNIT[expected.unit]}:
        return build_result(
            check,
            CheckOutcome.MATCH,
            expected,
            extracted,
            f"Printed {printed} equals the expected {wanted}.",
        )
    return build_result(
        check,
        CheckOutcome.DISCREPANCY,
        expected,
        extracted,
        f"Label states {printed}; expected {wanted}.",
    )


def build_result(
    check_id: CheckId,
    outcome: CheckOutcome,
    expected: str | Measurement | None,
    extracted: ExtractedField | None,
    explanation: str | None,
    observed: str | Measurement | None = None,
) -> CheckResult:
    """Build a result with one evidence reference per observation."""
    field_id = FieldId(check_id.value)
    observations = extracted.observations if extracted else ()
    if observed is None:
        observed = " | ".join(dict.fromkeys(o.raw_text for o in observations)) or None
    evidence = tuple(
        EvidenceRef(field_id, index, o.image_id) for index, o in enumerate(observations)
    )
    return CheckResult(
        check_id=check_id,
        outcome=outcome,
        field_id=field_id,
        expected_value=expected,
        observed_value=observed,
        explanation=explanation,
        evidence=evidence,
    )
