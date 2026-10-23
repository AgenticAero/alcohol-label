from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image

from alcohol_label import intake
from alcohol_label.intake import UploadedImage, build_application
from alcohol_label.schemas import FieldId, Measurement, Unit


def _image(fmt: str = "PNG", size: tuple[int, int] = (8, 8)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size).save(buffer, format=fmt)
    return buffer.getvalue()


def _form(**overrides):
    values = {
        "application_id": "APP-1",
        "brand": "Stone's Throw",
        "class_type": "Straight Bourbon Whiskey",
        "alcohol_content": "45",
        "net_contents": "750",
        "net_contents_unit": Unit.MILLILITER,
        "producer_name": "Stone Distilling Co.",
        "producer_address": "Louisville, KY",
        "is_imported": False,
        "country_of_origin": "",
        "uploads": [UploadedImage("front.png", _image())],
    }
    values.update(overrides)
    return build_application(**values)


def test_valid_single_image():
    result = _form()
    assert result.errors == ()
    app = result.application
    assert app.alcohol_content == Measurement(Decimal(45), Unit.PERCENT_ABV)
    assert app.net_contents == Measurement(Decimal(750), Unit.MILLILITER)
    assert [(i.image_id, i.uri) for i in app.images] == [("image-1", "front.png")]
    assert app.missing_required_fields() == ()


def test_valid_two_images_get_generated_ids():
    uploads = [
        UploadedImage("front.png", _image()),
        UploadedImage("b.jpg", _image("JPEG")),
    ]
    app = _form(uploads=uploads).application
    assert [i.image_id for i in app.images] == ["image-1", "image-2"]
    assert [i.uri for i in app.images] == ["front.png", "b.jpg"]


def test_blank_values_stay_none_and_are_reported_missing():
    app = _form(brand="  ", alcohol_content="").application
    assert app.brand is None
    assert app.alcohol_content is None
    assert set(app.missing_required_fields()) == {
        FieldId.BRAND,
        FieldId.ALCOHOL_CONTENT,
    }


def test_country_required_only_when_imported():
    assert (
        FieldId.COUNTRY_OF_ORIGIN not in _form().application.missing_required_fields()
    )
    imported = _form(is_imported=True).application
    assert FieldId.COUNTRY_OF_ORIGIN in imported.missing_required_fields()


@pytest.mark.parametrize("text", ["abc", "0", "-5", "NaN", "Infinity"])
def test_invalid_abv_returns_error(text):
    result = _form(alcohol_content=text)
    assert result.application is None
    assert any("Alcohol content" in e for e in result.errors)


def test_unsupported_and_corrupt_files_rejected():
    gif = _image("GIF")
    for data in (gif, b"not an image"):
        result = _form(uploads=[UploadedImage("x", data)])
        assert result.application is None
        assert result.errors


def test_oversized_file_rejected(monkeypatch):
    monkeypatch.setattr(intake, "MAX_IMAGE_BYTES", 10)
    result = _form()
    assert any("larger than" in e for e in result.errors)


def test_too_many_pixels_rejected(monkeypatch):
    monkeypatch.setattr(intake, "MAX_IMAGE_PIXELS", 10)
    result = _form()
    assert any("megapixels" in e for e in result.errors)


def test_zero_and_three_images_rejected():
    assert _form(uploads=[]).application is None
    three = [UploadedImage(f"{n}.png", _image()) for n in range(3)]
    assert _form(uploads=three).application is None


def test_missing_fields_reported_even_with_other_errors():
    result = _form(is_imported=True, application_id="", uploads=[])
    assert result.application is None
    assert FieldId.COUNTRY_OF_ORIGIN in result.missing_fields
    assert _form(is_imported=False).missing_fields == ()
