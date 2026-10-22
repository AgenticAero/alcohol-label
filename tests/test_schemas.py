from decimal import Decimal

import pytest

from alcohol_label.schemas import (
    ApplicationData,
    BeverageCategory,
    CheckId,
    CheckOutcome,
    ExtractionState,
    FieldId,
    ImageReference,
    Measurement,
    Unit,
)


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


def _images(*ids: str) -> tuple[ImageReference, ...]:
    return tuple(ImageReference(i, f"file:///labels/{i}.jpg") for i in ids)


def _complete(**overrides):
    values = {
        "application_id": "app-001",
        "beverage_category": BeverageCategory.DISTILLED_SPIRITS,
        "is_imported": False,
        "images": _images("front"),
        "brand": "Old Tom",
        "class_type": "Straight Bourbon Whiskey",
        "alcohol_content": Measurement(Decimal("45.0"), Unit.PERCENT_ABV),
        "net_contents": Measurement(Decimal(750), Unit.MILLILITER),
        "producer_name": "Example Distillery",
        "producer_address": "1 Main St, Louisville, KY",
    }
    values.update(overrides)
    return ApplicationData(**values)


def test_application_data_keeps_decimal_units_and_separate_producer_fields():
    application = _complete(images=_images("front", "back"))

    assert application.alcohol_content == Measurement(Decimal("45.0"), Unit.PERCENT_ABV)
    assert application.net_contents.unit is Unit.MILLILITER
    assert application.producer_name != application.producer_address
    assert len(application.images) == 2
    assert application.missing_required_fields() == ()


def test_unsupplied_values_stay_none_and_are_reported_not_defaulted():
    application = ApplicationData(
        application_id="app-002",
        beverage_category=BeverageCategory.DISTILLED_SPIRITS,
        is_imported=False,
        images=_images("front"),
        brand="Old Tom",
    )

    assert application.alcohol_content is None
    assert application.country_of_origin is None
    assert application.missing_required_fields() == (
        FieldId.CLASS_TYPE,
        FieldId.ALCOHOL_CONTENT,
        FieldId.NET_CONTENTS,
        FieldId.PRODUCER_NAME,
        FieldId.PRODUCER_ADDRESS,
    )


def test_country_of_origin_is_required_only_for_imports():
    assert _complete().missing_required_fields() == ()
    imported = _complete(is_imported=True)
    assert imported.missing_required_fields() == (FieldId.COUNTRY_OF_ORIGIN,)
    with_country = _complete(is_imported=True, country_of_origin="Scotland")
    assert with_country.missing_required_fields() == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"images": ()},
        {"images": _images("a", "b", "c")},
        {"images": _images("a", "a")},
        {"brand": "  "},
        {"alcohol_content": Measurement(Decimal(45), Unit.MILLILITER)},
        {"net_contents": Measurement(Decimal(45), Unit.PERCENT_ABV)},
    ],
)
def test_structurally_invalid_application_data_is_rejected(overrides):
    with pytest.raises(ValueError):
        _complete(**overrides)


@pytest.mark.parametrize("value", [Decimal(0), Decimal(-1), Decimal("NaN"), 45.0])
def test_measurement_requires_positive_finite_decimal(value):
    with pytest.raises(ValueError):
        Measurement(value, Unit.PERCENT_ABV)
