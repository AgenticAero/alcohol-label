import base64
import json
import urllib.error
from io import BytesIO

from PIL import Image

from alcohol_label import extraction
from alcohol_label.extraction import ProviderConfig, extract_application
from alcohol_label.schemas import ErrorCode, ExtractionState, FieldId, ImageReference


def _image() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _response(fields: dict | None = None) -> dict:
    values = {
        field.value: {"text": f"value-{field.value}", "state": "observed"}
        for field in FieldId
    }
    if fields:
        values.update(fields)
    return {
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": json.dumps(values)},
                ]
            }
        ]
    }


def _config() -> ProviderConfig:
    return ProviderConfig("test-key", "test-model")


def test_provider_request_contains_image_and_fixed_instructions_only(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return BytesIO(b'{"id":"response"}')

    monkeypatch.setattr(extraction.urllib.request, "urlopen", fake_urlopen)
    image = _image()

    extraction._call_provider(image, _config())

    body = captured["body"]
    content = body["input"][0]["content"]
    image_url = content[1]["image_url"]
    assert base64.b64decode(image_url.split(",", 1)[1]) == image
    assert "expected" not in json.dumps(body).lower()
    assert body["store"] is False
    assert body["text"]["format"]["strict"] is True
    assert captured["timeout"] == extraction._TIMEOUT_SECONDS


def test_extract_application_preserves_equal_and_conflicting_image_observations(
    monkeypatch,
):
    responses = iter(
        [
            _response({FieldId.BRAND.value: {"text": "OLD TOM", "state": "observed"}}),
            _response(
                {FieldId.BRAND.value: {"text": "Old Tom Reserve", "state": "observed"}}
            ),
        ]
    )
    payloads = []

    def fake_call(data, config):
        payloads.append(data)
        return next(responses)

    monkeypatch.setattr(extraction, "_call_provider", fake_call)

    result = extract_application(
        [ImageReference("front", "front.png"), ImageReference("back", "back.png")],
        [b"front bytes", b"back bytes"],
        config=_config(),
    )

    brand = next(field for field in result.fields if field.field_id is FieldId.BRAND)
    assert brand.state is ExtractionState.CONFLICTING
    assert [(item.raw_text, item.image_id) for item in brand.observations] == [
        ("OLD TOM", "front"),
        ("Old Tom Reserve", "back"),
    ]
    class_type = next(
        field for field in result.fields if field.field_id is FieldId.CLASS_TYPE
    )
    assert class_type.state is ExtractionState.OBSERVED
    assert [item.image_id for item in class_type.observations] == ["front", "back"]
    assert result.errors == ()
    assert result.metadata.model == "test-model"
    assert payloads == [b"front bytes", b"back bytes"]


def test_warning_text_preserves_provider_text_verbatim(monkeypatch):
    raw_warning = "  GOVERNMENT WARNING:\r\n(1) Exact text.  "
    monkeypatch.setattr(
        extraction,
        "_call_provider",
        lambda data, config: _response(
            {FieldId.WARNING_TEXT.value: {"text": raw_warning, "state": "observed"}}
        ),
    )

    result = extract_application(
        [ImageReference("back", "back.png")], [b"back"], config=_config()
    )

    warning = next(
        field for field in result.fields if field.field_id is FieldId.WARNING_TEXT
    )
    assert warning.observations[0].raw_text == raw_warning
    assert warning.observations[0].image_id == "back"


def test_provider_failure_preserves_successful_image_observations(monkeypatch):
    calls = iter([_response(), urllib.error.URLError("private provider detail")])

    def fake_call(data, config):
        response = next(calls)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(extraction, "_call_provider", fake_call)

    result = extract_application(
        [ImageReference("front", "front.png"), ImageReference("back", "back.png")],
        [b"front", b"back"],
        config=_config(),
    )

    brand = next(field for field in result.fields if field.field_id is FieldId.BRAND)
    assert brand.state is ExtractionState.UNCERTAIN
    assert [(item.raw_text, item.image_id) for item in brand.observations] == [
        ("value-brand", "front")
    ]
    assert result.errors[0].code is ErrorCode.ENDPOINT_BLOCKED
    assert "private provider detail" not in result.errors[0].message


def test_url_error_wrapping_socket_timeout_maps_to_provider_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise urllib.error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(extraction, "_call_provider", timeout)

    result = extract_application(
        [ImageReference("front", "front.png")], [b"front"], config=_config()
    )

    assert result.errors[0].code is ErrorCode.PROVIDER_TIMEOUT
    assert result.errors[0].retryable


def test_malformed_provider_schema_becomes_processing_error(monkeypatch):
    malformed = _response()
    output_text = malformed["output"][0]["content"][0]["text"]
    fields = json.loads(output_text)
    del fields[FieldId.BRAND.value]
    malformed["output"][0]["content"][0]["text"] = json.dumps(fields)
    monkeypatch.setattr(extraction, "_call_provider", lambda data, config: malformed)

    result = extract_application(
        [ImageReference("front", "front.png")], [b"front"], config=_config()
    )

    assert result.fields
    assert all(field.state is ExtractionState.UNCERTAIN for field in result.fields)
    assert result.errors[0].code is ErrorCode.INVALID_PROVIDER_RESPONSE
    assert "did not match the extraction schema" in result.errors[0].message


def test_unconfigured_provider_returns_controlled_error(monkeypatch):
    monkeypatch.setattr(ProviderConfig, "from_environment", lambda: None)

    result = extract_application([ImageReference("front", "front.png")], [b"front"])

    assert result.fields == ()
    assert result.errors[0].code is ErrorCode.INTERNAL_ERROR
    assert result.metadata is None


def test_blank_base_url_uses_openai_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "")

    config = ProviderConfig.from_environment()

    assert config.base_url == "https://api.openai.com/v1"


def test_image_reference_and_payload_counts_must_match():
    try:
        extract_application(
            [ImageReference("front", "front.png"), ImageReference("back", "back.png")],
            [b"front"],
            config=_config(),
        )
    except ValueError as error:
        assert "one image payload" in str(error)
    else:
        raise AssertionError("mismatched image references and payloads were accepted")
