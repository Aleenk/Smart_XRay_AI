
from fastapi.testclient import TestClient
from backend import main, security


client = TestClient(main.app)


def test_login_success(monkeypatch):
    """Valid credentials should return an access token and public user data."""
    user = {
        "id": 1,
        "username": "test_doctor",
        "role": "DOCTOR",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    monkeypatch.setattr(
        main, "authenticate_user", lambda username, password: user
    )
    monkeypatch.setattr(
        main,
        "create_session",
        lambda user_id: (
            "fake-test-token",
            "2026-01-01T18:00:00+00:00",
        ),
    )
    monkeypatch.setattr(main, "log_event", lambda **kwargs: None)

    response = client.post(
        "/auth/login",
        json={
            "username": "test_doctor",
            "password": "CorrectPassword123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["access_token"] == "fake-test-token"
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "test_doctor"
    assert data["user"]["role"] == "DOCTOR"
    assert "password_hash" not in data["user"]
    assert "password_salt" not in data["user"]


def test_login_invalid_credentials(monkeypatch):
    """Invalid credentials should be rejected."""
    monkeypatch.setattr(
        main, "authenticate_user", lambda username, password: None
    )
    monkeypatch.setattr(main, "log_event", lambda **kwargs: None)

    response = client.post(
        "/auth/login",
        json={
            "username": "unknown_user",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_login_missing_password():
    """A request without a password should fail validation."""
    response = client.post(
        "/auth/login",
        json={"username": "test_doctor"},
    )

    assert response.status_code == 422


def test_admin_users_forbidden_for_doctor(monkeypatch):
    """A doctor should be rejected by the ADMIN role dependency."""
    from fastapi import HTTPException

    monkeypatch.setattr(main, "log_event", lambda **kwargs: None)

    doctor = {
        "id": 2,
        "username": "test_doctor",
        "role": "DOCTOR",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    dependency = security.require_roles("ADMIN")

    try:
        dependency(user=doctor)
        assert False, "A doctor should not have access"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == (
            "You do not have permission to perform this action."
        )


def test_admin_users_allowed_for_admin():
    """An admin should pass the ADMIN role dependency."""
    admin = {
        "id": 1,
        "username": "test_admin",
        "role": "ADMIN",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    dependency = security.require_roles("ADMIN")
    result = dependency(user=admin)

    assert result["username"] == "test_admin"
    assert result["role"] == "ADMIN"


def test_admin_users_endpoint_forbidden_for_doctor(monkeypatch):
    """The actual admin endpoint should reject a doctor."""
    doctor = {
        "id": 2,
        "username": "test_doctor",
        "role": "DOCTOR",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    main.app.dependency_overrides[security.get_current_user] = (
        lambda: doctor
    )
    monkeypatch.setattr(main, "log_event", lambda **kwargs: None)

    try:
        response = client.get(
            "/admin/users",
            headers={"Authorization": "Bearer fake-test-token"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "You do not have permission to perform this action."
        )
    finally:
        main.app.dependency_overrides.clear()


def test_admin_users_endpoint_allowed_for_admin(monkeypatch):
    """The actual admin endpoint should allow an admin."""
    admin = {
        "id": 1,
        "username": "test_admin",
        "role": "ADMIN",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    main.app.dependency_overrides[security.get_current_user] = (
        lambda: admin
    )
    monkeypatch.setattr(main, "log_event", lambda **kwargs: None)
    monkeypatch.setattr(main, "list_users", lambda: [admin])

    try:
        response = client.get(
            "/admin/users",
            headers={"Authorization": "Bearer fake-test-token"},
        )

        assert response.status_code == 200
        assert response.json()["users"][0]["username"] == "test_admin"
    finally:
        main.app.dependency_overrides.clear()


def test_logout_success(monkeypatch):
    """Logout should revoke the current session."""
    user = {
        "id": 1,
        "username": "test_doctor",
        "role": "DOCTOR",
        "active": 1,
        "created_at": "2026-01-01T10:00:00+00:00",
    }

    revoked_tokens = []

    main.app.dependency_overrides[security.get_current_user] = (
        lambda: user
    )
    monkeypatch.setattr(
        main,
        "revoke_session",
        lambda token: revoked_tokens.append(token),
    )
    monkeypatch.setattr(main, "log_event", lambda **kwargs: None)

    try:
        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer fake-test-token"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "logged_out"}
        assert revoked_tokens == ["fake-test-token"]
    finally:
        main.app.dependency_overrides.clear()


def test_auth_me_without_token():
    """Accessing the current-user endpoint without a token should fail."""
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication is required."


def test_auth_me_with_invalid_token():
    """An invalid session token should be rejected."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-test-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Session is invalid or expired."
