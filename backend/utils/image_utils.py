from io import BytesIO
from PIL import Image, UnidentifiedImageError


def prepare_xray_image(image_bytes: bytes):
    try:
        image = Image.open(
            BytesIO(image_bytes)
        )

        original_width, original_height = image.size
        original_mode = image.mode

        image = image.convert("RGB")

        resized_image = image.resize(
            (224, 224)
        )

        return {
            "image": resized_image,
            "original_width": original_width,
            "original_height": original_height,
            "original_mode": original_mode,
            "processed_width": 224,
            "processed_height": 224
        }

    except UnidentifiedImageError:
        raise ValueError(
            "The uploaded file is not a valid image."
        )