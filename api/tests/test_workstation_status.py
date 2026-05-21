from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.workstation_status import normalize_sam_account_name


def test_normalize_sam_account_name_handles_domain_prefix() -> None:
    assert normalize_sam_account_name(r"CORP\anderson.bandeira") == "anderson.bandeira"
    assert normalize_sam_account_name("anderson.bandeira@corp.local") == "anderson.bandeira"
    assert normalize_sam_account_name("") is None


def test_workstation_status_requires_token(monkeypatch) -> None:
    monkeypatch.setenv("WORKSTATION_STATUS_TOKEN", "expected-token")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/api/status",
        json={
            "computer": "PC-001",
            "user": r"CORP\anderson.bandeira",
            "ip": "10.0.0.10",
            "timestamp": datetime(2026, 5, 20, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 401


def test_workstation_status_persists_payload(monkeypatch) -> None:
    executed = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def execute(self, query, params):
            executed["query"] = query
            executed["params"] = params

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def cursor(self):
            return FakeCursor()

        def commit(self):
            executed["committed"] = True

    monkeypatch.setenv("WORKSTATION_STATUS_TOKEN", "expected-token")
    get_settings.cache_clear()
    monkeypatch.setattr("app.workstation_status.database_connection", lambda: FakeConnection())
    monkeypatch.setattr("app.workstation_status.audit_event", lambda *args, **kwargs: None)
    client = TestClient(app)

    response = client.post(
        "/api/status",
        headers={"X-Workstation-Token": "expected-token"},
        json={
            "computer": "PC-001",
            "user": r"CORP\anderson.bandeira",
            "ip": "10.0.0.10",
            "timestamp": datetime(2026, 5, 20, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["sam_account_name"] == "anderson.bandeira"
    assert executed["committed"] is True
    assert executed["params"][4] == "anderson.bandeira"
