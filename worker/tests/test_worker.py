from pathlib import Path

from app.main import (
    WorkerApiError,
    build_inventory_snapshot,
    create_worker_access_token,
    env_bool,
    env_int,
    env_list,
    inventory_snapshot,
    record_job,
    render_worker_metrics,
)


def test_env_bool_defaults_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_BOOL", raising=False)

    assert env_bool("MISSING_BOOL", True) is True


def test_env_int_defaults_when_invalid(monkeypatch) -> None:
    monkeypatch.setenv("BAD_INT", "invalid")

    assert env_int("BAD_INT", 30) == 30


def test_env_list_uses_pipe_separator(monkeypatch) -> None:
    monkeypatch.setenv("LIST_VALUE", "OU=A,DC=example,DC=local|OU=B,DC=example,DC=local")

    assert env_list("LIST_VALUE") == ["OU=A,DC=example,DC=local", "OU=B,DC=example,DC=local"]


def test_record_job_writes_jsonl(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))

    record_job("test_job", "success", count=1)

    content = Path(tmp_path / "worker-jobs.jsonl").read_text(encoding="utf-8")
    assert "test_job" in content
    assert "success" in content


def test_worker_access_token_is_jwt_shaped(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("WORKER_API_SUBJECT", "admanager-worker-test")

    token = create_worker_access_token()

    assert token.count(".") == 2


def test_inventory_snapshot_records_query_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    import app.main as worker_main

    def fake_api_request(path, token=None, payload=None):
        raise WorkerApiError(f"simulated failure for {path}")

    monkeypatch.setattr(worker_main, "api_request", fake_api_request)

    snapshot = build_inventory_snapshot()

    assert snapshot["summary"]["users"]["all"]["count"] == 0
    assert snapshot["summary"]["users"]["all"]["error"].startswith("simulated failure")


def test_inventory_snapshot_writes_latest_and_metrics(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    import app.main as worker_main

    def fake_api_request(path, token=None, payload=None):
        return {"count": 2}

    monkeypatch.setattr(worker_main, "api_request", fake_api_request)

    inventory_snapshot()
    metrics = render_worker_metrics()

    assert (tmp_path / "inventory-snapshot-latest.json").exists()
    assert 'admanager_inventory_objects{object_type="users",status="all"} 2' in metrics
    assert 'admanager_inventory_query_errors{object_type="users",status="all"} 0' in metrics


def test_inventory_snapshot_collects_segments_and_delta(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("WORKER_INVENTORY_USER_OUS", "OU=Users,DC=example,DC=local")

    import app.main as worker_main

    calls = {"count": 0}

    def fake_api_request(path, token=None, payload=None):
        calls["count"] += 1
        return {"count": calls["count"]}

    monkeypatch.setattr(worker_main, "api_request", fake_api_request)

    inventory_snapshot()
    inventory_snapshot()
    metrics = render_worker_metrics()

    assert 'admanager_inventory_segment_objects{object_type="users",segment="OU=Users,DC=example,DC=local",status="all"}' in metrics
    assert 'admanager_inventory_delta_objects{object_type="users",status="all"}' in metrics


def test_build_jobs_includes_workstation_status_retention() -> None:
    import app.main as worker_main

    job_names = {job.name for job in worker_main.build_jobs()}

    assert "workstation_status_retention" in job_names
