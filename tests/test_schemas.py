import json
from decimal import Decimal

import pytest

from alcohol_label.schemas import (
    _CHECK_FIELD,
    ApplicationData,
    BeverageCategory,
    BoundingBox,
    CheckId,
    CheckOutcome,
    CheckResult,
    ErrorCode,
    EvidenceLocation,
    EvidenceRef,
    ExtractedField,
    ExtractionState,
    FieldId,
    ImageReference,
    Measurement,
    Observation,
    ProcessingError,
    ProcessingStage,
    ReviewResponse,
    ReviewStatus,
    Unit,
    application_from_dict,
    application_to_dict,
    check_result_from_dict,
    check_result_to_dict,
    extracted_field_from_dict,
    extracted_field_to_dict,
    review_response_from_dict,
    review_response_to_dict,
    validate_review_evidence,
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


def test_observation_preserves_raw_text_separately_from_parsed_value():
    raw = "  Old Tom's  RESERVE\u2019 "
    obs = Observation(raw, "img-1", parsed_value=Decimal("45.0"))

    assert obs.raw_text == raw
    assert obs.parsed_value == Decimal("45.0")
    assert Observation(raw, "img-1").parsed_value is None


def test_observed_field_carries_source_image_and_location():
    box = BoundingBox(0.1, 0.2, 0.5, 0.4)
    obs = Observation(
        "45% Alc./Vol.", "img-2", location=EvidenceLocation(box, "crop-7")
    )
    field = ExtractedField(FieldId.ALCOHOL_CONTENT, ExtractionState.OBSERVED, (obs,))

    assert field.observations[0].image_id == "img-2"
    assert field.observations[0].location.box == box
    assert field.explanation is None


def test_extracted_field_copies_observations_to_immutable_tuple():
    observation = Observation("45% Alc./Vol.", "img-1")
    observations = [observation]

    field = ExtractedField(
        FieldId.ALCOHOL_CONTENT, ExtractionState.OBSERVED, observations
    )
    observations.clear()

    assert field.observations == (observation,)


def test_conflicting_observations_are_all_preserved_in_order():
    first = Observation("OLD TOM", "img-1")
    second = Observation("Old Tom Reserve", "img-2")
    field = ExtractedField(
        FieldId.BRAND,
        ExtractionState.CONFLICTING,
        (first, second),
        "Front and back labels disagree.",
    )

    assert field.observations == (first, second)


def test_unknowns_use_none_state_and_explanation_and_uncertain_may_hold_candidates():
    missing = ExtractedField(
        FieldId.NET_CONTENTS, ExtractionState.MISSING, explanation="Not in images."
    )
    uncertain = ExtractedField(
        FieldId.WARNING_TEXT,
        ExtractionState.UNCERTAIN,
        (Observation("GOVERNMENT WARN", "img-1"),),
        "Text is cut off.",
    )

    assert missing.observations == ()
    assert len(uncertain.observations) == 1


@pytest.mark.parametrize(
    ("state", "observations", "explanation"),
    [
        (ExtractionState.OBSERVED, (), None),
        (
            ExtractionState.OBSERVED,
            (Observation("a", "i"), Observation("b", "i")),
            None,
        ),
        (ExtractionState.MISSING, (Observation("a", "i"),), "x"),
        (ExtractionState.MISSING, (), None),
        (ExtractionState.UNCERTAIN, (), "  "),
        (ExtractionState.CONFLICTING, (Observation("a", "i"),), "x"),
        (
            ExtractionState.CONFLICTING,
            (Observation("a", "i"), Observation("a", "j")),
            "x",
        ),
        (
            ExtractionState.CONFLICTING,
            (Observation("a", "i"), Observation("b", "i")),
            None,
        ),
    ],
)
def test_extracted_field_state_rules_reject_inconsistent_records(
    state, observations, explanation
):
    with pytest.raises(ValueError):
        ExtractedField(FieldId.BRAND, state, observations, explanation)


@pytest.mark.parametrize(
    "build",
    [
        lambda: BoundingBox(0.5, 0.1, 0.4, 0.9),
        lambda: BoundingBox(0, 0, 1.2, 1),
        lambda: EvidenceLocation(),
        lambda: EvidenceLocation(crop_ref=" "),
        lambda: Observation("", "img-1"),
        lambda: Observation("text", " "),
    ],
)
def test_invalid_evidence_structures_are_rejected(build):
    with pytest.raises(ValueError):
        build()


def _ref(field_id=FieldId.BRAND, index=0, image_id="img-1"):
    return EvidenceRef(field_id, index, image_id)


def test_match_needs_no_explanation_and_keeps_values_and_evidence_order():
    refs = [_ref(), _ref(index=1, image_id="img-2")]
    result = CheckResult(
        CheckId.BRAND,
        CheckOutcome.MATCH,
        FieldId.BRAND,
        expected_value="Old Tom",
        observed_value="OLD TOM",
        evidence=refs,
    )

    assert result.explanation is None
    assert result.evidence == tuple(refs)
    assert [r.image_id for r in result.evidence] == ["img-1", "img-2"]


def test_discrepancy_with_evidence_and_unresolved_outcomes_with_reasons():
    CheckResult(
        CheckId.ALCOHOL_CONTENT,
        CheckOutcome.DISCREPANCY,
        FieldId.ALCOHOL_CONTENT,
        Measurement(Decimal(45), Unit.PERCENT_ABV),
        Measurement(Decimal(40), Unit.PERCENT_ABV),
        "Printed 40% differs from 45%.",
        (_ref(FieldId.ALCOHOL_CONTENT),),
    )
    for outcome in (
        CheckOutcome.NEEDS_REVIEW,
        CheckOutcome.NOT_APPLICABLE,
        CheckOutcome.NOT_EVALUATED,
    ):
        result = CheckResult(
            CheckId.COUNTRY_OF_ORIGIN,
            outcome,
            FieldId.COUNTRY_OF_ORIGIN,
            explanation="Reason recorded.",
        )
        assert result.observed_value is None


def test_warning_checks_are_separate_results_on_the_warning_field():
    results = [
        CheckResult(
            check,
            CheckOutcome.NOT_EVALUATED,
            explanation="Style evidence unavailable.",
        )
        for check in CheckId
        if check.value.startswith("warning_")
    ]

    assert len({r.check_id for r in results}) == 4
    assert CheckResult(
        CheckId.WARNING_HEADING_BOLD,
        CheckOutcome.NEEDS_REVIEW,
        FieldId.WARNING_TEXT,
        explanation="Weight uncertain.",
        evidence=(_ref(FieldId.WARNING_TEXT),),
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"check_id": CheckId.BRAND, "outcome": CheckOutcome.NEEDS_REVIEW},
        {
            "check_id": CheckId.BRAND,
            "outcome": CheckOutcome.NOT_EVALUATED,
            "explanation": " ",
        },
        {
            "check_id": CheckId.BRAND,
            "outcome": CheckOutcome.DISCREPANCY,
            "explanation": "Differs.",
        },
        {"check_id": CheckId.BRAND, "outcome": CheckOutcome.MATCH},
        {
            "check_id": CheckId.BRAND,
            "outcome": CheckOutcome.MATCH,
            "field_id": FieldId.CLASS_TYPE,
        },
        {
            "check_id": CheckId.WARNING_WORDING,
            "outcome": CheckOutcome.MATCH,
            "field_id": FieldId.BRAND,
        },
        {
            "check_id": CheckId.BRAND,
            "outcome": CheckOutcome.MATCH,
            "field_id": FieldId.BRAND,
            "evidence": (_ref(FieldId.CLASS_TYPE),),
        },
        {
            "check_id": CheckId.BRAND,
            "outcome": CheckOutcome.MATCH,
            "field_id": FieldId.BRAND,
            "observed_value": 45.0,
        },
    ],
)
def test_check_result_rejects_inconsistent_records(kwargs):
    kwargs.setdefault("field_id", None)
    with pytest.raises(ValueError):
        CheckResult(**kwargs)


@pytest.mark.parametrize(
    "build",
    [
        lambda: CheckResult("brand", CheckOutcome.MATCH, FieldId.BRAND),
        lambda: CheckResult(CheckId.BRAND, "match", FieldId.BRAND),
        lambda: CheckResult(
            CheckId.BRAND, CheckOutcome.MATCH, FieldId.BRAND, evidence=("img-1",)
        ),
        lambda: EvidenceRef("brand", 0, "img-1"),
        lambda: EvidenceRef(FieldId.BRAND, True, "img-1"),
        lambda: ExtractedField(FieldId.BRAND, "observed", (Observation("a", "i"),)),
    ],
)
def test_wrong_types_raise_type_error(build):
    with pytest.raises(TypeError):
        build()


@pytest.mark.parametrize(
    "build",
    [
        lambda: EvidenceRef(FieldId.BRAND, -1, "img-1"),
        lambda: EvidenceRef(FieldId.BRAND, 0, " "),
    ],
)
def test_invalid_evidence_refs_are_rejected(build):
    with pytest.raises(ValueError):
        build()


def _error(code=ErrorCode.PROVIDER_TIMEOUT, retryable=True):
    return ProcessingError(
        ProcessingStage.EXTRACTION, code, "Extraction did not finish.", retryable
    )


def _check_field(check):
    return _CHECK_FIELD[check]


def _result(check, outcome=CheckOutcome.MATCH):
    explanation = None if outcome is CheckOutcome.MATCH else "Reason recorded."
    evidence = ()
    if outcome is CheckOutcome.DISCREPANCY:
        evidence = (EvidenceRef(_check_field(check), 0, "img-1"),)
    return CheckResult(
        check,
        outcome,
        field_id=_check_field(check),
        explanation=explanation,
        evidence=evidence,
    )


def _all_results():
    return tuple(_result(c) for c in CheckId)


def test_error_codes_and_stages_are_not_outcomes_or_states():
    labels = {o.value for o in CheckOutcome} | {s.value for s in ExtractionState}
    failure_labels = {c.value for c in ErrorCode} | {s.value for s in ProcessingStage}
    assert not labels & failure_labels
    assert {
        "provider_timeout",
        "endpoint_blocked",
        "invalid_provider_response",
    } <= {c.value for c in ErrorCode}


def test_processing_error_records_failures_without_diagnostics_field():
    blocked = _error(ErrorCode.ENDPOINT_BLOCKED, retryable=False)

    assert blocked.retryable is False
    assert _error().retryable is True
    assert set(ProcessingError.__slots__) == {"stage", "code", "message", "retryable"}


def test_processing_error_rejects_blank_message_and_wrong_types():
    with pytest.raises(ValueError):
        ProcessingError(ProcessingStage.EXTRACTION, ErrorCode.INTERNAL_ERROR, " ", True)
    for args in (
        ("extraction", ErrorCode.INTERNAL_ERROR, "m", True),
        (ProcessingStage.EXTRACTION, "internal_error", "m", True),
        (ProcessingStage.EXTRACTION, ErrorCode.INTERNAL_ERROR, None, True),
        (ProcessingStage.EXTRACTION, ErrorCode.INTERNAL_ERROR, "m", 1),
    ):
        with pytest.raises(TypeError):
            ProcessingError(*args)
    with pytest.raises(TypeError):
        ProcessingError(ProcessingStage.EXTRACTION, ErrorCode.INTERNAL_ERROR, "m")


def test_review_response_keeps_partial_results_and_errors_separate():
    partial = [_result(CheckId.BRAND)]
    errors = [_error()]
    response = ReviewResponse("app-001", partial, errors)

    assert response.check_results == tuple(partial)
    assert response.processing_errors == tuple(errors)
    assert response.status is ReviewStatus.INCOMPLETE
    assert response.all_clear is False


def test_complete_clear_review_is_all_clear_and_not_applicable_is_clear():
    response = ReviewResponse("app-001", _all_results())
    assert response.status is ReviewStatus.COMPLETE
    assert response.all_clear is True

    domestic = tuple(
        _result(c, CheckOutcome.NOT_APPLICABLE)
        if c is CheckId.COUNTRY_OF_ORIGIN
        else _result(c)
        for c in CheckId
    )
    assert ReviewResponse("app-001", domestic).all_clear is True


@pytest.mark.parametrize(
    "outcome",
    [CheckOutcome.DISCREPANCY, CheckOutcome.NEEDS_REVIEW, CheckOutcome.NOT_EVALUATED],
)
def test_unresolved_or_failed_checks_block_all_clear_but_stay_visible(outcome):
    results = (_result(CheckId.BRAND, outcome),) + tuple(
        _result(c) for c in CheckId if c is not CheckId.BRAND
    )
    response = ReviewResponse("app-001", results)

    assert response.status is ReviewStatus.COMPLETE
    assert response.all_clear is False
    assert response.check_results[0].outcome is outcome


def test_processing_error_or_missing_check_blocks_all_clear():
    assert ReviewResponse("app-001", _all_results(), (_error(),)).all_clear is False
    assert ReviewResponse("app-001", _all_results()[:-1]).all_clear is False
    empty = ReviewResponse("app-001")
    assert empty.status is ReviewStatus.INCOMPLETE
    assert empty.all_clear is False


def test_review_response_rejects_invalid_structure():
    brand = _result(CheckId.BRAND)
    with pytest.raises(ValueError):
        ReviewResponse(" ")
    with pytest.raises(ValueError):
        ReviewResponse("app-001", (brand, brand))
    with pytest.raises(TypeError):
        ReviewResponse("app-001", ("brand",))
    with pytest.raises(TypeError):
        ReviewResponse("app-001", (), ("timeout",))


# Contract examples: each scenario returns (application, extracted fields, response).


def _fill(results):
    """Complete a partial result list with plain matches for the other checks."""
    given = {r.check_id for r in results}
    return tuple(results) + tuple(_result(c) for c in CheckId if c not in given)


def _example_match():
    app = _complete(images=_images("front"))
    brand = ExtractedField(
        FieldId.BRAND,
        ExtractionState.OBSERVED,
        (
            Observation(
                "OLD  TOM\u00ae",
                "front",
                parsed_value="OLD TOM",
                location=EvidenceLocation(BoundingBox(0.1, 0.2, 0.6, 0.3)),
            ),
        ),
    )
    abv = ExtractedField(
        FieldId.ALCOHOL_CONTENT,
        ExtractionState.OBSERVED,
        (Observation("45.0% Alc./Vol.", "front", parsed_value=Decimal("45.0")),),
    )
    results = [
        CheckResult(
            CheckId.BRAND,
            CheckOutcome.MATCH,
            FieldId.BRAND,
            expected_value="Old Tom",
            observed_value="OLD TOM",
            evidence=(EvidenceRef(FieldId.BRAND, 0, "front"),),
        ),
        CheckResult(
            CheckId.ALCOHOL_CONTENT,
            CheckOutcome.MATCH,
            FieldId.ALCOHOL_CONTENT,
            expected_value=Measurement(Decimal("45.0"), Unit.PERCENT_ABV),
            observed_value=Decimal("45.0"),
            evidence=(EvidenceRef(FieldId.ALCOHOL_CONTENT, 0, "front"),),
        ),
    ]
    return app, (brand, abv), ReviewResponse("app-001", _fill(results))


def _example_missing_expected_value():
    app = _complete(brand=None)
    brand = ExtractedField(
        FieldId.BRAND,
        ExtractionState.OBSERVED,
        (Observation("OLD TOM", "front"),),
    )
    result = CheckResult(
        CheckId.BRAND,
        CheckOutcome.NOT_EVALUATED,
        FieldId.BRAND,
        observed_value="OLD TOM",
        explanation="No expected brand was supplied.",
    )
    return app, (brand,), ReviewResponse("app-001", _fill([result]))


def _example_unknown_extraction():
    app = _complete()
    abv = ExtractedField(
        FieldId.ALCOHOL_CONTENT,
        ExtractionState.UNCERTAIN,
        (Observation("4?.0% Alc./Vol.", "front"),),
        explanation="Digit obscured by glare.",
    )
    net = ExtractedField(
        FieldId.NET_CONTENTS,
        ExtractionState.MISSING,
        explanation="No net contents statement found in the supplied images.",
    )
    results = [
        CheckResult(
            CheckId.ALCOHOL_CONTENT,
            CheckOutcome.NEEDS_REVIEW,
            FieldId.ALCOHOL_CONTENT,
            explanation="Reading is uncertain.",
        ),
        CheckResult(
            CheckId.NET_CONTENTS,
            CheckOutcome.NEEDS_REVIEW,
            FieldId.NET_CONTENTS,
            explanation="Not found in the supplied images; not proof of absence.",
        ),
    ]
    return app, (abv, net), ReviewResponse("app-001", _fill(results))


def _example_conflicting_observations():
    app = _complete(images=_images("front", "back"))
    class_type = ExtractedField(
        FieldId.CLASS_TYPE,
        ExtractionState.CONFLICTING,
        (
            Observation("Straight Bourbon Whiskey", "front"),
            Observation("Kentucky Bourbon", "back"),
        ),
        explanation="Front and back differ.",
    )
    result = CheckResult(
        CheckId.CLASS_TYPE,
        CheckOutcome.NEEDS_REVIEW,
        FieldId.CLASS_TYPE,
        expected_value="Straight Bourbon Whiskey",
        explanation="Observations conflict; none was selected.",
        evidence=(
            EvidenceRef(FieldId.CLASS_TYPE, 0, "front"),
            EvidenceRef(FieldId.CLASS_TYPE, 1, "back"),
        ),
    )
    return app, (class_type,), ReviewResponse("app-001", _fill([result]))


def _example_provider_timeout():
    app = _complete()
    brand = ExtractedField(
        FieldId.BRAND, ExtractionState.OBSERVED, (Observation("OLD TOM", "front"),)
    )
    partial = [
        CheckResult(
            CheckId.BRAND,
            CheckOutcome.MATCH,
            FieldId.BRAND,
            evidence=(EvidenceRef(FieldId.BRAND, 0, "front"),),
        )
    ]
    response = ReviewResponse(
        "app-001",
        partial,
        [
            ProcessingError(
                ProcessingStage.EXTRACTION,
                ErrorCode.PROVIDER_TIMEOUT,
                "Extraction timed out. Try again.",
                True,
            )
        ],
    )
    return app, (brand,), response


_EXAMPLES = [
    _example_match,
    _example_missing_expected_value,
    _example_unknown_extraction,
    _example_conflicting_observations,
    _example_provider_timeout,
]


def _through_json(data):
    return json.loads(json.dumps(data))


@pytest.mark.parametrize("example", _EXAMPLES)
def test_examples_round_trip_through_json_and_resolve_evidence(example):
    app, fields, response = example()

    assert application_from_dict(_through_json(application_to_dict(app))) == app
    for field in fields:
        assert (
            extracted_field_from_dict(_through_json(extracted_field_to_dict(field)))
            == field
        )
    restored = review_response_from_dict(
        _through_json(review_response_to_dict(response))
    )
    assert restored == response
    assert restored.status is response.status
    validate_review_evidence(restored, app, fields)


def test_examples_have_expected_review_semantics():
    match = _example_match()[2]
    assert match.all_clear is True

    app, _, missing = _example_missing_expected_value()
    assert FieldId.BRAND in app.missing_required_fields()
    assert missing.all_clear is False

    assert _example_unknown_extraction()[2].all_clear is False
    assert _example_conflicting_observations()[2].all_clear is False

    timeout = _example_provider_timeout()[2]
    assert timeout.status is ReviewStatus.INCOMPLETE
    assert timeout.all_clear is False
    assert timeout.check_results[0].outcome is CheckOutcome.MATCH
    assert all(r.outcome is not CheckOutcome.DISCREPANCY for r in timeout.check_results)


def test_round_trip_preserves_raw_text_decimals_states_and_evidence_ids():
    app, fields, _response = _example_match()
    data = _through_json(extracted_field_to_dict(fields[0]))
    assert data["observations"][0]["raw_text"] == "OLD  TOM\u00ae"

    abv = _through_json(extracted_field_to_dict(fields[1]))
    assert abv["observations"][0]["parsed_value"] == {"decimal": "45.0"}
    restored_abv = extracted_field_from_dict(abv)
    assert str(restored_abv.observations[0].parsed_value) == "45.0"
    assert isinstance(restored_abv.observations[0].parsed_value, Decimal)

    restored_app = application_from_dict(_through_json(application_to_dict(app)))
    assert restored_app.alcohol_content.value == Decimal("45.0")
    assert str(restored_app.alcohol_content.value) == "45.0"

    conflicting = _example_conflicting_observations()
    restored_field = extracted_field_from_dict(
        _through_json(extracted_field_to_dict(conflicting[1][0]))
    )
    assert restored_field.state is ExtractionState.CONFLICTING
    assert [o.raw_text for o in restored_field.observations] == [
        "Straight Bourbon Whiskey",
        "Kentucky Bourbon",
    ]
    restored = check_result_from_dict(
        _through_json(check_result_to_dict(conflicting[2].check_results[0]))
    )
    assert restored.evidence == (
        EvidenceRef(FieldId.CLASS_TYPE, 0, "front"),
        EvidenceRef(FieldId.CLASS_TYPE, 1, "back"),
    )


def test_deserialized_status_is_recomputed_not_trusted():
    data = _through_json(review_response_to_dict(_example_provider_timeout()[2]))
    data["status"] = "complete"
    data["all_clear"] = True

    restored = review_response_from_dict(data)

    assert restored.status is ReviewStatus.INCOMPLETE
    assert restored.all_clear is False


def test_serialized_response_keeps_errors_and_results_separate():
    data = review_response_to_dict(_example_provider_timeout()[2])

    assert data["processing_errors"][0]["code"] == "provider_timeout"
    assert {r["outcome"] for r in data["check_results"]} <= {
        o.value for o in CheckOutcome
    }
    assert set(data["processing_errors"][0]) == {
        "stage",
        "code",
        "message",
        "retryable",
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("application_id"),
        lambda d: d.update(beverage_category="mead"),
        lambda d: d.update(images=[]),
        lambda d: d.update(alcohol_content={"decimal": "45"}),
        lambda d: d.update(
            alcohol_content={"measurement": {"value": "4x", "unit": "percent_abv"}}
        ),
        lambda d: d.update(
            net_contents={"measurement": {"value": "750", "unit": "percent_abv"}}
        ),
    ],
)
def test_invalid_application_data_is_rejected_on_deserialization(mutate):
    data = _through_json(application_to_dict(_example_match()[0]))
    mutate(data)
    with pytest.raises(ValueError):
        application_from_dict(data)


def test_invalid_combinations_are_rejected_on_deserialization():
    result = _through_json(check_result_to_dict(_example_match()[2].check_results[0]))
    result["outcome"] = "discrepancy"
    result["evidence"] = []
    with pytest.raises(ValueError):
        check_result_from_dict(result)

    field = _through_json(extracted_field_to_dict(_example_match()[1][0]))
    field["state"] = "missing"
    with pytest.raises(ValueError):
        extracted_field_from_dict(field)

    with pytest.raises(TypeError):
        review_response_from_dict("not an object")
    with pytest.raises(TypeError):
        check_result_from_dict(
            {
                **check_result_to_dict(_example_match()[2].check_results[0]),
                "expected_value": {"decimal": 45},
            }
        )


def test_review_evidence_boundary_reports_every_unresolved_reference():
    app, fields, _ = _example_conflicting_observations()
    bad = [
        EvidenceRef(FieldId.CLASS_TYPE, 5, "front"),
        EvidenceRef(FieldId.CLASS_TYPE, 0, "back"),
        EvidenceRef(FieldId.CLASS_TYPE, 1, "elsewhere"),
    ]
    response = ReviewResponse(
        "app-001",
        [
            CheckResult(
                CheckId.CLASS_TYPE,
                CheckOutcome.NEEDS_REVIEW,
                FieldId.CLASS_TYPE,
                explanation="Conflict.",
                evidence=bad,
            )
        ],
    )

    with pytest.raises(ValueError) as error:
        validate_review_evidence(response, app, fields)

    message = str(error.value)
    assert "no such observation" in message
    assert "image differs" in message
    assert "unsupplied image 'elsewhere'" in message


def test_review_evidence_boundary_rejects_reference_to_unextracted_field():
    app, _, response = _example_match()

    with pytest.raises(ValueError, match="no extracted field"):
        validate_review_evidence(response, app, ())
