from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


WORKER_STARTED_AT = time.time()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def log(message: str, **fields: object) -> None:
    payload = {
        "timestamp": utc_now().isoformat(),
        "service": "worker",
        "message": message,
        **fields,
    }
    print(json.dumps(payload, default=str), flush=True)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split("|") if item.strip()]


def report_dir() -> Path:
    return Path(os.getenv("REPORT_OUTPUT_DIR", "/app/reports"))


def api_base_url() -> str:
    return os.getenv("WORKER_API_BASE_URL", "http://api:8080").rstrip("/")


def record_job(job_name: str, status: str, **fields: object) -> None:
    directory = report_dir()
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": utc_now().isoformat(),
        "job_name": job_name,
        "status": status,
        **fields,
    }
    with (directory / "worker-jobs.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
    write_worker_metrics()


def read_job_records() -> list[dict[str, object]]:
    directory = report_dir()
    directory.mkdir(parents=True, exist_ok=True)
    jobs_file = directory / "worker-jobs.jsonl"
    records: list[dict[str, object]] = []
    if not jobs_file.exists():
        return records

    for line in jobs_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def write_worker_metrics() -> None:
    directory = report_dir()
    directory.mkdir(parents=True, exist_ok=True)
    records = read_job_records()
    total = 0
    errors = 0
    for payload in records:
        total += 1
        if payload.get("status") == "error":
            errors += 1
    metrics = {
        "timestamp": utc_now().isoformat(),
        "jobs_total": total,
        "jobs_error_total": errors,
    }
    (directory / "worker-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def latest_inventory_snapshot() -> dict[str, object] | None:
    path = report_dir() / "inventory-snapshot-latest.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def prometheus_label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def timestamp_to_epoch(value: object) -> float:
    if not isinstance(value, str):
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def render_worker_metrics() -> str:
    records = read_job_records()
    status_totals: dict[str, int] = {}
    last_run_by_job: dict[str, float] = {}
    inventory = latest_inventory_snapshot()

    for record in records:
        status = str(record.get("status") or "unknown")
        job_name = str(record.get("job_name") or "unknown")
        status_totals[status] = status_totals.get(status, 0) + 1
        last_run_by_job[job_name] = max(
            last_run_by_job.get(job_name, 0.0),
            timestamp_to_epoch(record.get("timestamp")),
        )

    lines = [
        "# HELP admanager_worker_info Worker metadata.",
        "# TYPE admanager_worker_info gauge",
        'admanager_worker_info{service="worker"} 1',
        "# HELP admanager_worker_uptime_seconds Worker uptime in seconds.",
        "# TYPE admanager_worker_uptime_seconds gauge",
        f"admanager_worker_uptime_seconds {max(time.time() - WORKER_STARTED_AT, 0):.0f}",
        "# HELP admanager_worker_jobs_total Worker job executions by status.",
        "# TYPE admanager_worker_jobs_total counter",
    ]

    for status in sorted(status_totals):
        lines.append(f'admanager_worker_jobs_total{{status="{prometheus_label(status)}"}} {status_totals[status]}')

    lines.extend(
        [
            "# HELP admanager_worker_job_last_run_timestamp Last worker job execution time as Unix timestamp.",
            "# TYPE admanager_worker_job_last_run_timestamp gauge",
        ]
    )
    for job_name in sorted(last_run_by_job):
        lines.append(
            f'admanager_worker_job_last_run_timestamp{{job_name="{prometheus_label(job_name)}"}} {last_run_by_job[job_name]:.0f}'
        )

    if inventory:
        generated_at = timestamp_to_epoch(inventory.get("generated_at"))
        lines.extend(
            [
                "# HELP admanager_inventory_snapshot_timestamp Last AD inventory snapshot time as Unix timestamp.",
                "# TYPE admanager_inventory_snapshot_timestamp gauge",
                f"admanager_inventory_snapshot_timestamp {generated_at:.0f}",
                "# HELP admanager_inventory_objects AD inventory object counts by object type and status.",
                "# TYPE admanager_inventory_objects gauge",
            ]
        )
        summary = inventory.get("summary")
        if isinstance(summary, dict):
            for object_type, statuses in sorted(summary.items()):
                if not isinstance(statuses, dict):
                    continue
                for status_name, details in sorted(statuses.items()):
                    if not isinstance(details, dict):
                        continue
                    labels = (
                        f'object_type="{prometheus_label(object_type)}",'
                        f'status="{prometheus_label(status_name)}"'
                    )
                    lines.append(f"admanager_inventory_objects{{{labels}}} {int(details.get('count') or 0)}")

            lines.extend(
                [
                    "# HELP admanager_inventory_query_capped AD inventory queries that reached the configured limit.",
                    "# TYPE admanager_inventory_query_capped gauge",
                ]
            )
            for object_type, statuses in sorted(summary.items()):
                if not isinstance(statuses, dict):
                    continue
                for status_name, details in sorted(statuses.items()):
                    if not isinstance(details, dict):
                        continue
                    labels = (
                        f'object_type="{prometheus_label(object_type)}",'
                        f'status="{prometheus_label(status_name)}"'
                    )
                    lines.append(f"admanager_inventory_query_capped{{{labels}}} {1 if details.get('capped') else 0}")

            lines.extend(
                [
                    "# HELP admanager_inventory_query_errors AD inventory query failures.",
                    "# TYPE admanager_inventory_query_errors gauge",
                ]
            )
            for object_type, statuses in sorted(summary.items()):
                if not isinstance(statuses, dict):
                    continue
                for status_name, details in sorted(statuses.items()):
                    if not isinstance(details, dict):
                        continue
                    labels = (
                        f'object_type="{prometheus_label(object_type)}",'
                        f'status="{prometheus_label(status_name)}"'
                    )
                    lines.append(f"admanager_inventory_query_errors{{{labels}}} {1 if details.get('error') else 0}")

        segments = inventory.get("segments")
        if isinstance(segments, dict):
            lines.extend(
                [
                    "# HELP admanager_inventory_segment_objects AD inventory object counts by segment.",
                    "# TYPE admanager_inventory_segment_objects gauge",
                ]
            )
            for object_type, segment_payload in sorted(segments.items()):
                if not isinstance(segment_payload, dict):
                    continue
                for segment_name, statuses in sorted(segment_payload.items()):
                    if not isinstance(statuses, dict):
                        continue
                    for status_name, details in sorted(statuses.items()):
                        if not isinstance(details, dict):
                            continue
                        labels = (
                            f'object_type="{prometheus_label(object_type)}",'
                            f'segment="{prometheus_label(segment_name)}",'
                            f'status="{prometheus_label(status_name)}"'
                        )
                        lines.append(f"admanager_inventory_segment_objects{{{labels}}} {int(details.get('count') or 0)}")

            lines.extend(
                [
                    "# HELP admanager_inventory_segment_query_errors AD inventory segment query failures.",
                    "# TYPE admanager_inventory_segment_query_errors gauge",
                ]
            )
            for object_type, segment_payload in sorted(segments.items()):
                if not isinstance(segment_payload, dict):
                    continue
                for segment_name, statuses in sorted(segment_payload.items()):
                    if not isinstance(statuses, dict):
                        continue
                    for status_name, details in sorted(statuses.items()):
                        if not isinstance(details, dict):
                            continue
                        labels = (
                            f'object_type="{prometheus_label(object_type)}",'
                            f'segment="{prometheus_label(segment_name)}",'
                            f'status="{prometheus_label(status_name)}"'
                        )
                        lines.append(
                            f"admanager_inventory_segment_query_errors{{{labels}}} {1 if details.get('error') else 0}"
                        )

        delta = inventory.get("delta_from_previous")
        if isinstance(delta, dict):
            summary_delta = delta.get("summary")
            if isinstance(summary_delta, dict):
                lines.extend(
                    [
                        "# HELP admanager_inventory_delta_objects Difference from previous snapshot.",
                        "# TYPE admanager_inventory_delta_objects gauge",
                    ]
                )
                for object_type, statuses in sorted(summary_delta.items()):
                    if not isinstance(statuses, dict):
                        continue
                    for status_name, value in sorted(statuses.items()):
                        labels = (
                            f'object_type="{prometheus_label(object_type)}",'
                            f'status="{prometheus_label(status_name)}"'
                        )
                        lines.append(f"admanager_inventory_delta_objects{{{labels}}} {int(value or 0)}")

    return "\n".join(lines) + "\n"


class WorkerMetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}\n')
            return

        if self.path == "/metrics":
            payload = render_worker_metrics().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def start_metrics_server() -> None:
    if not env_bool("WORKER_METRICS_ENABLED", True):
        return

    port = env_int("WORKER_METRICS_LISTEN_PORT", 9100)

    def serve() -> None:
        try:
            server = HTTPServer(("0.0.0.0", port), WorkerMetricsHandler)
            log("worker metrics server started", port=port)
            server.serve_forever()
        except Exception as exc:
            log("worker metrics server failed", error=exc.__class__.__name__)

    thread = threading.Thread(target=serve, name="worker-metrics-server", daemon=True)
    thread.start()


def cleanup_old_reports() -> None:
    retention_days = env_int("REPORT_RETENTION_DAYS", 90)
    cutoff = utc_now() - timedelta(days=retention_days)
    deleted = 0
    directory = report_dir()
    directory.mkdir(parents=True, exist_ok=True)

    for path in directory.glob("*.csv"):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified_at < cutoff:
            path.unlink()
            deleted += 1

    record_job("report_cleanup", "success", deleted=deleted, retention_days=retention_days)
    log("job completed", job_name="report_cleanup", deleted=deleted)


class WorkerApiError(RuntimeError):
    pass


def api_request(path: str, token: str | None = None, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{api_base_url()}{path}", data=data, headers=headers, method="POST" if data else "GET")
    if path == "/auth/token":
        bootstrap_token = os.getenv("APP_BOOTSTRAP_ADMIN_TOKEN", "")
        if bootstrap_token:
            request.add_header("X-Bootstrap-Token", bootstrap_token)

    try:
        with urlopen(request, timeout=env_int("WORKER_API_TIMEOUT_SECONDS", 30)) as response:
            response_payload = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise WorkerApiError(f"API request failed with HTTP {exc.code}: {path}: {error_body}") from exc
    except URLError as exc:
        raise WorkerApiError(f"API request failed: {exc.__class__.__name__}") from exc

    try:
        parsed = json.loads(response_payload)
    except json.JSONDecodeError as exc:
        raise WorkerApiError(f"API returned invalid JSON: {path}") from exc
    if not isinstance(parsed, dict):
        raise WorkerApiError(f"API returned unexpected payload: {path}")
    return parsed


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def create_worker_access_token() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise WorkerApiError("JWT_SECRET is not configured for worker token generation")

    now = int(time.time())
    expires_at = now + env_int("WORKER_API_TOKEN_EXPIRE_SECONDS", 3600)
    payload = {
        "sub": os.getenv("WORKER_API_SUBJECT", "admanager-worker"),
        "roles": ["auditor"],
        "exp": expires_at,
        "iat": now,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(signature)}"


def get_worker_api_token() -> str:
    if os.getenv("WORKER_API_TOKEN_MODE", "local").lower() == "local":
        return create_worker_access_token()

    response = api_request(
        "/auth/token",
        payload={
            "subject": os.getenv("WORKER_API_SUBJECT", "admanager-worker"),
            "roles": ["auditor"],
        },
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise WorkerApiError("API token response did not include access_token")
    return token


def collect_inventory_count(
    token: str,
    object_type: str,
    status_name: str,
    extra_params: dict[str, object],
) -> dict[str, object]:
    limit = env_int("WORKER_INVENTORY_QUERY_LIMIT", 500)
    params = {"status": status_name, "limit": limit, **extra_params}
    try:
        response = api_request(f"/{object_type}?{urlencode(params)}", token=token)
        count = int(response.get("count") or 0)
        return {
            "count": count,
            "limit": limit,
            "capped": count >= limit,
            "error": None,
        }
    except WorkerApiError as exc:
        log(
            "inventory query failed",
            object_type=object_type,
            status=status_name,
            error=exc.__class__.__name__,
            error_detail=str(exc)[:500],
        )
        return {
            "count": 0,
            "limit": limit,
            "capped": False,
            "error": str(exc)[:500],
        }


USER_INVENTORY_STATUSES = [
    "all",
    "active",
    "disabled",
    "locked",
    "inactive",
    "never_logged_on",
    "password_never_expires",
]

GROUP_INVENTORY_STATUSES = ["all", "empty", "with_members", "without_description", "without_owner"]

COMPUTER_INVENTORY_STATUSES = [
    "all",
    "active",
    "disabled",
    "inactive",
    "never_logged_on",
    "servers",
    "workstations",
    "domain_controllers",
    "old_machine_password",
    "missing_metadata",
]


def collect_status_summary(
    token: str,
    object_type: str,
    statuses: list[str],
    extra_params: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        status_name: collect_inventory_count(token, object_type, status_name, extra_params)
        for status_name in statuses
    }


def inventory_segments(
    token: str,
    inactive_days: int,
    machine_password_days: int,
) -> dict[str, dict[str, dict[str, dict[str, object]]]]:
    segments: dict[str, dict[str, dict[str, dict[str, object]]]] = {
        "users": {},
        "groups": {},
        "computers": {},
    }

    for ou_dn in env_list("WORKER_INVENTORY_USER_OUS"):
        segments["users"][ou_dn] = collect_status_summary(
            token,
            "users",
            USER_INVENTORY_STATUSES,
            {"inactive_days": inactive_days, "ou_dn": ou_dn},
        )

    for ou_dn in env_list("WORKER_INVENTORY_GROUP_OUS"):
        segments["groups"][ou_dn] = collect_status_summary(
            token,
            "groups",
            GROUP_INVENTORY_STATUSES,
            {"ou_dn": ou_dn},
        )

    for ou_dn in env_list("WORKER_INVENTORY_COMPUTER_OUS"):
        segments["computers"][ou_dn] = collect_status_summary(
            token,
            "computers",
            COMPUTER_INVENTORY_STATUSES,
            {
                "inactive_days": inactive_days,
                "machine_password_days": machine_password_days,
                "ou_dn": ou_dn,
            },
        )

    return {object_type: values for object_type, values in segments.items() if values}


def summary_delta(previous: dict[str, object] | None, current: dict[str, object]) -> dict[str, object] | None:
    if not previous:
        return None

    previous_summary = previous.get("summary")
    current_summary = current.get("summary")
    if not isinstance(previous_summary, dict) or not isinstance(current_summary, dict):
        return None

    delta: dict[str, dict[str, int]] = {}
    for object_type, statuses in current_summary.items():
        if not isinstance(statuses, dict):
            continue
        previous_statuses = previous_summary.get(object_type)
        if not isinstance(previous_statuses, dict):
            continue
        delta[object_type] = {}
        for status_name, details in statuses.items():
            if not isinstance(details, dict):
                continue
            previous_details = previous_statuses.get(status_name)
            if not isinstance(previous_details, dict):
                continue
            delta[object_type][status_name] = int(details.get("count") or 0) - int(
                previous_details.get("count") or 0
            )

    return {"summary": delta}


def build_inventory_snapshot() -> dict[str, object]:
    token = get_worker_api_token()
    inactive_days = env_int("WORKER_INVENTORY_INACTIVE_DAYS", 90)
    machine_password_days = env_int("WORKER_INVENTORY_MACHINE_PASSWORD_DAYS", 90)
    summary = {
        "users": collect_status_summary(token, "users", USER_INVENTORY_STATUSES, {"inactive_days": inactive_days}),
        "groups": collect_status_summary(token, "groups", GROUP_INVENTORY_STATUSES, {}),
        "computers": collect_status_summary(
            token,
            "computers",
            COMPUTER_INVENTORY_STATUSES,
            {
                "inactive_days": inactive_days,
                "machine_password_days": machine_password_days,
            },
        ),
    }
    segments = inventory_segments(token, inactive_days, machine_password_days)

    return {
        "generated_at": utc_now().isoformat(),
        "type": "ad_inventory_snapshot",
        "source": "api",
        "api_base_url": api_base_url(),
        "parameters": {
            "inactive_days": inactive_days,
            "machine_password_days": machine_password_days,
            "query_limit": env_int("WORKER_INVENTORY_QUERY_LIMIT", 500),
            "user_ous": env_list("WORKER_INVENTORY_USER_OUS"),
            "group_ous": env_list("WORKER_INVENTORY_GROUP_OUS"),
            "computer_ous": env_list("WORKER_INVENTORY_COMPUTER_OUS"),
        },
        "summary": summary,
        "segments": segments,
    }


def inventory_snapshot() -> None:
    directory = report_dir()
    directory.mkdir(parents=True, exist_ok=True)
    previous_snapshot = latest_inventory_snapshot()
    snapshot = build_inventory_snapshot()
    snapshot["delta_from_previous"] = summary_delta(previous_snapshot, snapshot)
    filename = f"inventory-snapshot-{utc_now().strftime('%Y%m%d%H%M%S')}.json"
    (directory / filename).write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "inventory-snapshot-latest.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    object_total = 0
    capped_queries = 0
    failed_queries = 0
    summary = snapshot.get("summary")
    if isinstance(summary, dict):
        for statuses in summary.values():
            if not isinstance(statuses, dict):
                continue
            all_details = statuses.get("all")
            if isinstance(all_details, dict):
                object_total += int(all_details.get("count") or 0)
            capped_queries += sum(
                1 for details in statuses.values() if isinstance(details, dict) and details.get("capped")
            )
            failed_queries += sum(
                1 for details in statuses.values() if isinstance(details, dict) and details.get("error")
            )

    record_job(
        "inventory_snapshot",
        "success",
        output_file=filename,
        objects=object_total,
        capped_queries=capped_queries,
        failed_queries=failed_queries,
    )
    log(
        "job completed",
        job_name="inventory_snapshot",
        output_file=filename,
        objects=object_total,
        failed_queries=failed_queries,
    )


def cleanup_audit_events() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        record_job("audit_retention", "skipped", reason="DATABASE_URL not configured")
        log("job skipped", job_name="audit_retention", reason="DATABASE_URL not configured")
        return

    retention_days = env_int("AUDIT_RETENTION_DAYS", 365)
    try:
        import psycopg

        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM audit_events WHERE occurred_at < now() - (%s || ' days')::interval",
                    (retention_days,),
                )
                deleted = cursor.rowcount
            connection.commit()
        record_job("audit_retention", "success", deleted=deleted, retention_days=retention_days)
        log("job completed", job_name="audit_retention", deleted=deleted)
    except Exception as exc:
        record_job("audit_retention", "error", error=exc.__class__.__name__)
        log("job failed", job_name="audit_retention", error=exc.__class__.__name__)


def cleanup_workstation_status_events() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        record_job("workstation_status_retention", "skipped", reason="DATABASE_URL not configured")
        log("job skipped", job_name="workstation_status_retention", reason="DATABASE_URL not configured")
        return

    retention_days = env_int("WORKSTATION_STATUS_RETENTION_DAYS", 90)
    try:
        import psycopg

        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM workstation_status_events WHERE received_at < now() - (%s || ' days')::interval",
                    (retention_days,),
                )
                deleted = cursor.rowcount
            connection.commit()
        record_job(
            "workstation_status_retention",
            "success",
            deleted=deleted,
            retention_days=retention_days,
        )
        log("job completed", job_name="workstation_status_retention", deleted=deleted)
    except Exception as exc:
        record_job("workstation_status_retention", "error", error=exc.__class__.__name__)
        log("job failed", job_name="workstation_status_retention", error=exc.__class__.__name__)


@dataclass
class ScheduledJob:
    name: str
    enabled: bool
    interval_seconds: int
    handler: Callable[[], None]
    last_run_at: datetime | None = None

    def due(self, now: datetime) -> bool:
        if not self.enabled:
            return False
        if self.last_run_at is None:
            return True
        return (now - self.last_run_at).total_seconds() >= self.interval_seconds

    def run(self) -> None:
        started_at = utc_now()
        try:
            self.handler()
            self.last_run_at = utc_now()
        except Exception as exc:
            self.last_run_at = utc_now()
            record_job(
                self.name,
                "error",
                error=exc.__class__.__name__,
                error_detail=str(exc)[:500],
                duration_seconds=(utc_now() - started_at).total_seconds(),
            )
            log("job failed", job_name=self.name, error=exc.__class__.__name__, error_detail=str(exc)[:500])


def build_jobs() -> list[ScheduledJob]:
    return [
        ScheduledJob(
            name="report_cleanup",
            enabled=env_bool("WORKER_REPORT_CLEANUP_ENABLED", True),
            interval_seconds=env_int("WORKER_SCHEDULER_INTERVAL_SECONDS", 30),
            handler=cleanup_old_reports,
        ),
        ScheduledJob(
            name="inventory_snapshot",
            enabled=env_bool("WORKER_INVENTORY_SNAPSHOT_ENABLED", True),
            interval_seconds=env_int("WORKER_INVENTORY_SNAPSHOT_INTERVAL_SECONDS", 86400),
            handler=inventory_snapshot,
        ),
        ScheduledJob(
            name="audit_retention",
            enabled=env_bool("WORKER_AUDIT_RETENTION_ENABLED", True),
            interval_seconds=env_int("WORKER_AUDIT_RETENTION_INTERVAL_SECONDS", 86400),
            handler=cleanup_audit_events,
        ),
        ScheduledJob(
            name="workstation_status_retention",
            enabled=env_bool("WORKER_WORKSTATION_STATUS_RETENTION_ENABLED", True),
            interval_seconds=env_int("WORKER_WORKSTATION_STATUS_RETENTION_INTERVAL_SECONDS", 86400),
            handler=cleanup_workstation_status_events,
        ),
    ]


def main() -> None:
    heartbeat_seconds = env_int("WORKER_HEARTBEAT_SECONDS", 60)
    scheduler_interval = env_int("WORKER_SCHEDULER_INTERVAL_SECONDS", 30)
    jobs = build_jobs()
    last_heartbeat_at: datetime | None = None
    start_metrics_server()

    log(
        "worker started",
        app_env=os.getenv("APP_ENV", "development"),
        enabled_jobs=[job.name for job in jobs if job.enabled],
    )

    while True:
        now = utc_now()
        if last_heartbeat_at is None or (now - last_heartbeat_at).total_seconds() >= heartbeat_seconds:
            log("worker heartbeat")
            last_heartbeat_at = now

        for job in jobs:
            if job.due(now):
                log("job started", job_name=job.name)
                job.run()

        time.sleep(scheduler_interval)


if __name__ == "__main__":
    main()
