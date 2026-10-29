
import base64
from io import BytesIO

from PIL import Image

from backend.model.inference import (
    DISEASE_LABELS,
    generate_gradcam,
)


def test_gradcam_returns_valid_image():
    image = Image.new("RGB", (224, 224), color=(128, 128, 128))

    result = generate_gradcam(image, "Pneumonia")

    assert result["finding"] == "Pneumonia"
    assert isinstance(result["attention_map"], str)
    assert result["attention_map"].startswith("data:image/png;base64,")
    assert 0.0 <= result["probability"] <= 1.0

    encoded = result["attention_map"].split(",", 1)[1]
    image_bytes = base64.b64decode(encoded)

    with Image.open(BytesIO(image_bytes)) as heatmap:
        heatmap.verify()


def test_gradcam_rejects_unsupported_finding():
    image = Image.new("RGB", (224, 224), color=(128, 128, 128))

    try:
        generate_gradcam(image, "No Finding")
    except ValueError:
        return

    raise AssertionError("Expected ValueError for unsupported finding")
