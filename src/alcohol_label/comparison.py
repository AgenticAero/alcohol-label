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
    StyleJudgement,
    Unit,
    WarningStyleObservation,
)

_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'"})
_WARNING_TEXT = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth "
    "defects. (2) Consumption of alcoholic beverages impairs your ability to "
    "drive a car or operate machinery, and may cause health problems."
)
_WARNING_SOURCE = (
    "https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16/section-16.21"
)
_WARNING_HEADING = "GOVERNMENT WARNING"


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


def _normalize_layout_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def compare_warning_wording(extracted: ExtractedField | None) -> CheckResult:
    """Compare the complete warning to the reviewed eCFR text, ignoring layout whitespace."""
    check = CheckId.WARNING_WORDING
    unresolved = unresolved_result(check, _WARNING_TEXT, extracted)
    if unresolved is not None:
        return unresolved
    observed = extracted.observations[0].raw_text
    if _normalize_layout_whitespace(observed) == _normalize_layout_whitespace(
        _WARNING_TEXT
    ):
        return build_result(check, CheckOutcome.MATCH, _WARNING_TEXT, extracted, None)
    return build_result(
        check,
        CheckOutcome.DISCREPANCY,
        _WARNING_TEXT,
        extracted,
        f"Observed warning wording differs from the canonical text in 27 CFR 16.21 ({_WARNING_SOURCE}).",
    )


def compare_warning_heading_case(extracted: ExtractedField | None) -> CheckResult:
    """Check uppercase heading independently from the complete warning wording."""
    check = CheckId.WARNING_HEADING_CASE
    unresolved = unresolved_result(check, _WARNING_HEADING, extracted)
    if unresolved is not None:
        return unresolved
    observed = extracted.observations[0].raw_text
    normalized = _normalize_layout_whitespace(observed)
    heading = re.match(r"government\s+warning(?=[:\s]|$)", normalized, re.IGNORECASE)
    if heading is None:
        return build_result(
            check,
            CheckOutcome.DISCREPANCY,
            _WARNING_HEADING,
            extracted,
            "The required Government Warning heading was not found at the start of the observed warning.",
        )
    if heading.group() == _WARNING_HEADING:
        return build_result(
            check, CheckOutcome.MATCH, _WARNING_HEADING, extracted, None
        )
    return build_result(
        check,
        CheckOutcome.DISCREPANCY,
        _WARNING_HEADING,
        extracted,
        "The Government Warning heading must be uppercase.",
    )


_STYLE_NOTE = "Judged from the image; physical type size is not assessed."
_JUDGEMENT_WORDS = {
    StyleJudgement.BOLD: "bold",
    StyleJudgement.NOT_BOLD: "not bold",
}


def _style_result(
    check: CheckId,
    outcome: CheckOutcome,
    expected: str,
    observed: str | None,
    explanation: str | None,
    evidence: tuple[EvidenceRef, ...] = (),
) -> CheckResult:
    return CheckResult(
        check_id=check,
        outcome=outcome,
        field_id=FieldId.WARNING_TEXT,
        expected_value=expected,
        observed_value=observed,
        explanation=explanation,
        evidence=evidence,
    )


def _compare_style(
    check: CheckId,
    part: str,
    required: StyleJudgement,
    styles: tuple[WarningStyleObservation, ...],
    extracted: ExtractedField | None,
) -> CheckResult:
    """Judge one warning part; style counts only where the warning text was read."""
    expected = _JUDGEMENT_WORDS[required]
    review = CheckOutcome.NEEDS_REVIEW
    if not styles:
        return _style_result(
            check,
            review,
            expected,
            None,
            f"No visual {part} weight assessment is available for this review "
            "(the extraction adapter returned none); inspect the label image.",
        )
    read_at = {
        o.image_id: index
        for index, o in enumerate(extracted.observations if extracted else ())
    }
    usable = [s for s in styles if s.image_id in read_at]
    if not usable:
        images = ", ".join(sorted({s.image_id for s in styles}))
        return _style_result(
            check,
            review,
            expected,
            None,
            f"The warning text was not read in image {images}, where {part} "
            "weight was assessed; inspect the label image.",
        )
    evidence = tuple(
        EvidenceRef(FieldId.WARNING_TEXT, read_at[s.image_id], s.image_id)
        for s in usable
    )
    if extracted.state is ExtractionState.UNCERTAIN:
        return _style_result(
            check,
            review,
            expected,
            None,
            f"The warning text could not be read reliably, so the {part} "
            "weight judgement is not accepted; inspect the label image.",
            evidence,
        )
    judgements = [(s, getattr(s, part)) for s in usable]
    unsure = [(s, j) for s, j in judgements if j is StyleJudgement.UNCERTAIN]
    if unsure:
        detail = "; ".join(f"image {s.image_id}: {s.reason}" for s, _ in unsure)
        return _style_result(
            check,
            review,
            expected,
            None,
            f"The visual {part} weight is uncertain ({detail}). "
            "Inspect the label image.",
            evidence,
        )
    seen = {j for _, j in judgements}
    if len(seen) > 1:
        listed = ", ".join(
            f"image {s.image_id}: {_JUDGEMENT_WORDS[j]}" for s, j in judgements
        )
        return _style_result(
            check,
            review,
            expected,
            None,
            f"Images disagree on {part} weight ({listed}); none was selected.",
            evidence,
        )
    judgement = seen.pop()
    observed = _JUDGEMENT_WORDS[judgement]
    if judgement is required:
        return _style_result(
            check, CheckOutcome.MATCH, expected, observed, _STYLE_NOTE, evidence
        )
    return _style_result(
        check,
        CheckOutcome.DISCREPANCY,
        expected,
        observed,
        f"The {part} appears {observed} in the image; it should be {expected}. "
        + _STYLE_NOTE,
        evidence,
    )


def compare_warning_heading_bold(
    styles: tuple[WarningStyleObservation, ...],
    extracted: ExtractedField | None,
) -> CheckResult:
    """Heading must look bold; unresolved style is never a pass."""
    return _compare_style(
        CheckId.WARNING_HEADING_BOLD, "heading", StyleJudgement.BOLD, styles, extracted
    )


def compare_warning_body_not_bold(
    styles: tuple[WarningStyleObservation, ...],
    extracted: ExtractedField | None,
) -> CheckResult:
    """Body must not look bold; unresolved style is never a pass."""
    return _compare_style(
        CheckId.WARNING_BODY_NOT_BOLD,
        "body",
        StyleJudgement.NOT_BOLD,
        styles,
        extracted,
    )


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


_STREET_TYPES = {
    "st": "street",
    "ave": "avenue",
    "rd": "road",
    "blvd": "boulevard",
    "dr": "drive",
    "ln": "lane",
    "ct": "court",
    "hwy": "highway",
    "pkwy": "parkway",
    "pl": "place",
}


def normalize_address(text: str) -> str:
    """Brand normalization, periods dropped, street-type abbreviations spelled out."""
    text = normalize_brand(text).replace(".", "")
    return re.sub(r"\w+", lambda m: _STREET_TYPES.get(m.group(), m.group()), text)


def _contains_phrase(haystack: str, needle: str) -> bool:
    """Whole-phrase containment; letters, digits and hyphens do not bound a phrase."""
    return bool(re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", haystack))


def _contains_segments(haystack: str, needle: str) -> bool:
    """True when the comma-separated segments of needle are a consecutive run."""
    hay = [p.strip() for p in haystack.split(",") if p.strip()]
    want = [p.strip() for p in needle.split(",") if p.strip()]
    return any(hay[i : i + len(want)] == want for i in range(len(hay) - len(want) + 1))


def compare_producer_address(
    expected: str | None, extracted: ExtractedField | None
) -> CheckResult:
    """Match when the expected address equals, or is a whole comma-separated run of, the printed one."""
    check = CheckId.PRODUCER_ADDRESS
    unresolved = unresolved_result(check, expected, extracted)
    if unresolved is not None:
        return unresolved
    raw = extracted.observations[0].raw_text
    want, seen = normalize_address(expected), normalize_address(raw)
    if want == seen:
        note = (
            None
            if expected == raw
            else "Matches after case, whitespace, period and street-type normalization."
        )
        return build_result(check, CheckOutcome.MATCH, expected, extracted, note)
    if _contains_segments(seen, want):
        return build_result(
            check,
            CheckOutcome.MATCH,
            expected,
            extracted,
            "Expected address appears within the printed address.",
        )
    return build_result(
        check,
        CheckOutcome.DISCREPANCY,
        expected,
        extracted,
        "Label address differs from the expected address after normalization.",
    )


_ORIGIN_PHRASE = re.compile(
    r"\s*(?:product\s+of|produce\s+of|made\s+in)\s+", re.IGNORECASE
)


def strip_origin_phrase(text: str) -> str:
    """Remove one recognized phrase at the very start; leave other text untouched."""
    m = _ORIGIN_PHRASE.match(text)
    if m and text[m.end() :].strip():
        return text[m.end() :]
    return text


def compare_country_of_origin(
    expected: str | None, extracted: ExtractedField | None, is_imported: bool
) -> CheckResult:
    """Imports only; origin is never inferred from an address or other wording."""
    check = CheckId.COUNTRY_OF_ORIGIN
    if not is_imported:
        return build_result(
            check,
            CheckOutcome.NOT_APPLICABLE,
            expected,
            extracted,
            "Product is not imported, so country of origin is not required.",
        )
    if expected is not None and (
        extracted is None or extracted.state is ExtractionState.MISSING
    ):
        return build_result(
            check,
            CheckOutcome.NEEDS_REVIEW,
            expected,
            extracted,
            "Country of origin was not observed in the supplied images; "
            "additional evidence is needed.",
        )
    unresolved = unresolved_result(check, expected, extracted)
    if unresolved is not None:
        return unresolved
    raw = extracted.observations[0].raw_text
    value = strip_origin_phrase(raw)
    shown = f'Observed "{raw}" read as "{value.strip()}"'
    if normalize_brand(expected) == normalize_brand(value):
        note = (
            None
            if expected == raw
            else f"{shown}; matches after phrase, case and whitespace normalization."
        )
        return build_result(check, CheckOutcome.MATCH, expected, extracted, note)
    return build_result(
        check,
        CheckOutcome.DISCREPANCY,
        expected,
        extracted,
        f'{shown}; differs from the expected "{expected}".',
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
    field_id = (
        FieldId.WARNING_TEXT
        if check_id.value.startswith("warning_")
        else FieldId(check_id.value)
    )
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
