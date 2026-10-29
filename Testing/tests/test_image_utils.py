
from io import BytesIO

import pytest
from PIL import Image

from backend.utils.image_utils import prepare_xray_image


def create_test_image(image_format="PNG", mode="RGB"):
    image = Image.new(mode, (400, 300), color=128)
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def test_prepare_image_returns_rgb_224():
    image_bytes = create_test_image()

    result = prepare_xray_image(image_bytes)

    assert result["image"].size == (224, 224)
    assert result["image"].mode == "RGB"
    assert result["original_width"] == 400
    assert result["original_height"] == 300
    assert result["processed_width"] == 224
    assert result["processed_height"] == 224


def test_prepare_grayscale_image():
    image_bytes = create_test_image(mode="L")

    result = prepare_xray_image(image_bytes)

    assert result["image"].mode == "RGB"
    assert result["image"].size == (224, 224)
    assert result["original_mode"] == "L"


def test_invalid_image_raises_value_error():
    with pytest.raises(ValueError):
        prepare_xray_image(b"this is not an image")
