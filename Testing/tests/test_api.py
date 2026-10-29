
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app
from backend import security


client = TestClient(app)


@pytest.fixture
def authenticated_client():
    """Provide an authenticated test user without creating a real session."""
    user = {
        "id": 1,
        "username": "test_doctor",
        "role": "DOCTOR",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    app.dependency_overrides[security.get_current_user] = lambda: user

    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def make_png():
    image = Image.new("RGB", (300, 300), color=(128, 128, 128))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_endpoint_accepts_png(authenticated_client):
    with make_png() as image_file:
        response = authenticated_client.post(
            "/predict",
            files={
                "file": (
                    "test.png",
                    image_file,
                    "image/png",
                )
            },
        )

    assert response.status_code == 200

    result = response.json()

    assert result["filename"] == "test.png"
    assert "predictions" in result
    assert "detected_findings" in result
    assert "summary" in result


def test_predict_rejects_unsupported_file_type(authenticated_client):
    response = authenticated_client.post(
        "/predict",
        files={
            "file": (
                "test.txt",
                b"not an image",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_gradcam_rejects_unsupported_finding(authenticated_client):
    with make_png() as image_file:
        response = authenticated_client.post(
            "/gradcam",
            data={"finding": "No Finding"},
            files={
                "file": (
                    "test.png",
                    image_file,
                    "image/png",
                )
            },
        )

    assert response.status_code == 400
