
from pathlib import Path

import pytest
from PIL import Image

from backend.model.inference import (
    TARGET_LABELS,
    DISEASE_LABELS,
    THRESHOLDS,
    predict_xray,
)


@pytest.fixture(scope="module")
def sample_image():
    # Synthetic image for checking inference behavior,
    # not for evaluating medical accuracy.
    return Image.new("RGB", (224, 224), color=(128, 128, 128))


def test_expected_labels_exist():
    assert DISEASE_LABELS == [
        "Pneumonia",
        "Pneumothorax",
        "Effusion",
        "Cardiomegaly",
    ]
    assert "No Finding" in TARGET_LABELS


def test_thresholds_exist_for_all_diseases():
    for label in DISEASE_LABELS:
        assert label in THRESHOLDS
        assert 0.0 <= float(THRESHOLDS[label]) <= 1.0


def test_prediction_output_is_valid(sample_image):
    result = predict_xray(sample_image)

    assert set(result["predictions"]) == set(DISEASE_LABELS)

    for label in DISEASE_LABELS:
        probability = result["predictions"][label]
        assert isinstance(probability, float)
        assert 0.0 <= probability <= 1.0

    assert isinstance(result["detected_findings"], list)
    assert isinstance(result["summary"], str)
    assert isinstance(result["no_selected_finding_detected"], bool)

    for label in DISEASE_LABELS:
        finding = result["findings"][label]
        assert finding["potential_finding"] == (
            finding["probability"] >= finding["threshold"]
        )
