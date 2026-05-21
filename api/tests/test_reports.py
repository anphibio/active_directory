from datetime import UTC, datetime
import json

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.reports import InventorySnapshotPayload, _csv_text, _json_ready
from app.security import Role


def test_json_ready_serializes_datetime() -> None:
    value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    assert _json_ready(value) == "2026-01-02T03:04:05+00:00"


def test_csv_text_includes_headers_and_rows() -> None:
    content = _csv_text(
        [
            {"sam_account_name": "user1", "enabled": True},
            {"sam_account_name": "user2", "enabled": False},
        ]
    )

    assert "sam_account_name" in content
    assert "enabled" in content
    assert "user1" in content
    assert "user2" in content


def test_inventory_snapshot_payload_accepts_worker_summary() -> None:
    payload = InventorySnapshotPayload(
        generated_at=datetime(2026, 5, 20, 0, 0, tzinfo=UTC),
        type="ad_inventory_snapshot",
        source="api",
        summary={
            "users": {
                "active": {
                    "count": 10,
                    "limit": 500,
                    "capped": False,
                    "error": None,
                }
            }
        },
    )

    assert payload.summary["users"]["active"]["count"] == 10


def test_inventory_snapshot_endpoint_reads_latest_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("APP_BOOTSTRAP_ADMIN_TOKEN", "test-bootstrap-token")
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()
    (tmp_path / "inventory-snapshot-latest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-05-20T00:00:00+00:00",
                "type": "ad_inventory_snapshot",
                "source": "api",
                "summary": {"users": {"all": {"count": 3}}},
            }
        ),
        encoding="utf-8",
    )
    client = TestClient(app)

    token_response = client.post(
        "/auth/token",
        headers={"X-Bootstrap-Token": "test-bootstrap-token"},
        json={"subject": "tester", "roles": [Role.viewer.value]},
    )
    token = token_response.json()["access_token"]
    response = client.get(
        "/reports/inventory-snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["summary"]["users"]["all"]["count"] == 3


def test_worker_status_endpoint_reads_jobs_and_metrics(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("APP_BOOTSTRAP_ADMIN_TOKEN", "test-bootstrap-token")
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()
    (tmp_path / "worker-metrics.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-20T01:00:00+00:00",
                "jobs_total": 2,
                "jobs_error_total": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "worker-jobs.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-05-20T00:59:00+00:00",
                        "job_name": "inventory_snapshot",
                        "status": "error",
                        "error": "failed",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-05-20T01:00:00+00:00",
                        "job_name": "report_cleanup",
                        "status": "success",
                        "deleted": 0,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    client = TestClient(app)

    token_response = client.post(
        "/auth/token",
        headers={"X-Bootstrap-Token": "test-bootstrap-token"},
        json={"subject": "tester", "roles": [Role.auditor.value]},
    )
    token = token_response.json()["access_token"]
    response = client.get(
        "/reports/worker-status?limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["jobs_total"] == 2
    assert response.json()["jobs_error_total"] == 1
    assert len(response.json()["last_jobs"]) == 2
