import csv
import json
from datetime import UTC, datetime
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.audit import audit_event
from app.computers import ComputerStatus, search_computers
from app.config import get_settings
from app.groups import GroupStatus, search_groups
from app.security import Permission, Principal, require_permission
from app.users import UserStatus, search_users


router = APIRouter(prefix="/reports", tags=["reports"])


class ReportFormat(StrEnum):
    json = "json"
    csv = "csv"


class ReportHistoryItem(BaseModel):
    report_id: str
    report_type: str
    format: ReportFormat
    generated_at: datetime
    generated_by: str
    row_count: int
    parameters: dict[str, Any]
    output_file: str | None = None


class ReportPayload(BaseModel):
    metadata: ReportHistoryItem
    items: list[dict[str, Any]]


class InventorySnapshotPayload(BaseModel):
    generated_at: datetime
    type: str
    source: str
    api_base_url: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    segments: dict[str, Any] = Field(default_factory=dict)
    delta_from_previous: dict[str, Any] | None = None


class WorkerJobRecord(BaseModel):
    timestamp: datetime
    job_name: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class WorkerMetricsPayload(BaseModel):
    timestamp: datetime | None = None
    jobs_total: int = 0
    jobs_error_total: int = 0
    last_jobs: list[WorkerJobRecord] = Field(default_factory=list)
    last_success_by_job: dict[str, datetime] = Field(default_factory=dict)
    last_error_by_job: dict[str, datetime] = Field(default_factory=dict)


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _model_to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return _json_ready(item.model_dump())
    if isinstance(item, dict):
        return _json_ready(item)
    return _json_ready(dict(item))


def _csv_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%d/%m/%Y %H:%M")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.astimezone(UTC).strftime("%d/%m/%Y %H:%M")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, list):
        return "; ".join(str(_csv_ready(item)) for item in value)
    if isinstance(value, dict):
        return json.dumps(_json_ready(value), ensure_ascii=False)
    return value


def _write_history(metadata: ReportHistoryItem) -> None:
    settings = get_settings()
    report_dir = Path(settings.report_output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    history_file = report_dir / "report-history.jsonl"
    with history_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(_json_ready(metadata.model_dump()), ensure_ascii=False) + "\n")


def _csv_text(rows: list[dict[str, Any]]) -> str:
    buffer = StringIO()
    fieldnames = sorted({key for row in rows for key in row.keys()})
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_ready(value) for key, value in row.items()})
    return buffer.getvalue()


def _csv_response(report_id: str, content: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.csv"'},
    )


def _read_json_file(path: Path, not_found_detail: str) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{not_found_detail} could not be read.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{not_found_detail} has an invalid format.",
        )
    return payload


def _read_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker jobs history could not be read.",
        ) from exc

    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _report_response(
    report_type: str,
    report_format: ReportFormat,
    principal: Principal,
    parameters: dict[str, Any],
    rows: list[dict[str, Any]],
) -> ReportPayload | Response:
    report_id = f"{report_type}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    settings = get_settings()
    report_dir = Path(settings.report_output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(report_dir / f"{report_id}.csv") if report_format == ReportFormat.csv else None
    metadata = ReportHistoryItem(
        report_id=report_id,
        report_type=report_type,
        format=report_format,
        generated_at=datetime.now(UTC),
        generated_by=principal.subject,
        row_count=len(rows),
        parameters=_json_ready(parameters),
        output_file=output_file,
    )
    _write_history(metadata)
    audit_event(
        "report_generated",
        operator=principal.subject,
        report_type=report_type,
        report_format=report_format.value,
        row_count=len(rows),
    )
    if report_format == ReportFormat.csv:
        csv_content = _csv_text(rows)
        if output_file:
            Path(output_file).write_text(csv_content, encoding="utf-8")
        return _csv_response(report_id, csv_content)
    return ReportPayload(metadata=metadata, items=rows)


@router.get("/users", response_model=ReportPayload)
def users_report(
    principal: Annotated[Principal, Depends(require_permission(Permission.run_reports))],
    report_format: Annotated[ReportFormat, Query(alias="format")] = ReportFormat.json,
    status_filter: Annotated[UserStatus, Query(alias="status")] = UserStatus.active,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    group_dn: Annotated[str | None, Query(max_length=500)] = None,
    ou_dn: Annotated[str | None, Query(max_length=500)] = None,
    inactive_days: Annotated[int, Query(ge=1, le=3650)] = 90,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> ReportPayload | Response:
    users = search_users(status_filter, query, group_dn, inactive_days, limit, ou_dn)
    parameters = {
        "status": status_filter.value,
        "query_present": bool(query),
        "group_filter_present": bool(group_dn),
        "ou_filter_present": bool(ou_dn),
        "inactive_days": inactive_days,
        "limit": limit,
    }
    return _report_response(
        "users",
        report_format,
        principal,
        parameters,
        [_model_to_dict(user) for user in users],
    )


@router.get("/groups", response_model=ReportPayload)
def groups_report(
    principal: Annotated[Principal, Depends(require_permission(Permission.run_reports))],
    report_format: Annotated[ReportFormat, Query(alias="format")] = ReportFormat.json,
    status_filter: Annotated[GroupStatus, Query(alias="status")] = GroupStatus.all,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    ou_dn: Annotated[str | None, Query(max_length=500)] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> ReportPayload | Response:
    groups = search_groups(status_filter, query, limit, ou_dn)
    parameters = {
        "status": status_filter.value,
        "query_present": bool(query),
        "ou_filter_present": bool(ou_dn),
        "limit": limit,
    }
    return _report_response(
        "groups",
        report_format,
        principal,
        parameters,
        [_model_to_dict(group) for group in groups],
    )


@router.get("/computers", response_model=ReportPayload)
def computers_report(
    principal: Annotated[Principal, Depends(require_permission(Permission.run_reports))],
    report_format: Annotated[ReportFormat, Query(alias="format")] = ReportFormat.json,
    status_filter: Annotated[ComputerStatus, Query(alias="status")] = ComputerStatus.active,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    ou_dn: Annotated[str | None, Query(max_length=500)] = None,
    operating_system: Annotated[str | None, Query(max_length=120)] = None,
    inactive_days: Annotated[int, Query(ge=1, le=3650)] = 90,
    machine_password_days: Annotated[int, Query(ge=1, le=3650)] = 90,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> ReportPayload | Response:
    computers = search_computers(
        status_filter,
        query,
        ou_dn,
        operating_system,
        inactive_days,
        machine_password_days,
        limit,
    )
    parameters = {
        "status": status_filter.value,
        "query_present": bool(query),
        "ou_filter_present": bool(ou_dn),
        "operating_system_filter_present": bool(operating_system),
        "inactive_days": inactive_days,
        "machine_password_days": machine_password_days,
        "limit": limit,
    }
    return _report_response(
        "computers",
        report_format,
        principal,
        parameters,
        [_model_to_dict(computer) for computer in computers],
    )


@router.get("/history", response_model=list[ReportHistoryItem])
def report_history(
    _: Annotated[Principal, Depends(require_permission(Permission.read_audit))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ReportHistoryItem]:
    settings = get_settings()
    history_file = Path(settings.report_output_dir) / "report-history.jsonl"
    if not history_file.exists():
        return []

    lines = history_file.read_text(encoding="utf-8").splitlines()[-limit:]
    return [ReportHistoryItem(**json.loads(line)) for line in lines if line.strip()]


@router.get("/inventory-snapshot", response_model=InventorySnapshotPayload)
def inventory_snapshot(
    principal: Annotated[Principal, Depends(require_permission(Permission.run_reports))],
) -> InventorySnapshotPayload:
    settings = get_settings()
    snapshot_file = Path(settings.report_output_dir) / "inventory-snapshot-latest.json"
    payload = _read_json_file(snapshot_file, "Inventory snapshot has not been generated yet.")

    audit_event(
        "inventory_snapshot_read",
        operator=principal.subject,
        generated_at=payload.get("generated_at"),
    )
    return InventorySnapshotPayload(**payload)


@router.get("/worker-status", response_model=WorkerMetricsPayload)
def worker_status(
    principal: Annotated[Principal, Depends(require_permission(Permission.read_audit))],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> WorkerMetricsPayload:
    settings = get_settings()
    report_dir = Path(settings.report_output_dir)
    metrics_file = report_dir / "worker-metrics.json"
    jobs_file = report_dir / "worker-jobs.jsonl"

    metrics = {}
    if metrics_file.exists():
        metrics = _read_json_file(metrics_file, "Worker metrics have not been generated yet.")

    job_records = _read_jsonl(jobs_file, limit)
    last_success_by_job: dict[str, datetime] = {}
    last_error_by_job: dict[str, datetime] = {}
    parsed_jobs: list[WorkerJobRecord] = []

    for record in job_records:
        details = {key: value for key, value in record.items() if key not in {"timestamp", "job_name", "status"}}
        job = WorkerJobRecord(
            timestamp=record.get("timestamp"),
            job_name=str(record.get("job_name") or "unknown"),
            status=str(record.get("status") or "unknown"),
            details=details,
        )
        parsed_jobs.append(job)
        if job.status == "error":
            last_error_by_job[job.job_name] = job.timestamp
        elif job.status == "success":
            last_success_by_job[job.job_name] = job.timestamp

    audit_event(
        "worker_status_read",
        operator=principal.subject,
        result_count=len(parsed_jobs),
    )
    return WorkerMetricsPayload(
        timestamp=metrics.get("timestamp"),
        jobs_total=int(metrics.get("jobs_total") or 0),
        jobs_error_total=int(metrics.get("jobs_error_total") or 0),
        last_jobs=parsed_jobs,
        last_success_by_job=last_success_by_job,
        last_error_by_job=last_error_by_job,
    )
