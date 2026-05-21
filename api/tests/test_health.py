from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.security import Role


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_summary_requires_authentication() -> None:
    client = TestClient(app)

    response = client.get("/config/summary")

    assert response.status_code == 401


def test_config_summary_does_not_expose_secrets(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("APP_BOOTSTRAP_ADMIN_TOKEN", "test-bootstrap-token")
    get_settings.cache_clear()
    client = TestClient(app)

    token_response = client.post(
        "/auth/token",
        headers={"X-Bootstrap-Token": "test-bootstrap-token"},
        json={"subject": "tester", "roles": [Role.admin.value]},
    )
    token = token_response.json()["access_token"]

    response = client.get("/config/summary", headers={"Authorization": f"Bearer {token}"})
    payload = response.json()

    assert response.status_code == 200
    assert "ad_bind_password" not in payload
    assert "jwt_secret" not in payload
    assert "session_secret" not in payload
    assert "encryption_key" not in payload


def test_missing_ad_variables_are_reported(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("APP_BOOTSTRAP_ADMIN_TOKEN", "test-bootstrap-token")
    get_settings.cache_clear()
    client = TestClient(app)

    token_response = client.post(
        "/auth/token",
        headers={"X-Bootstrap-Token": "test-bootstrap-token"},
        json={"subject": "tester", "roles": [Role.admin.value]},
    )
    token = token_response.json()["access_token"]
    response = client.get("/config/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert "missing_ad_variables" in response.json()
