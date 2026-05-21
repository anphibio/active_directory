import hmac
import ipaddress
import json
from datetime import UTC, datetime
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.audit import audit_event
from app.config import get_settings
from app.database import database_connection
from app.security import Permission, Principal, require_permission


router = APIRouter(tags=["workstation-status"])


class WorkstationStatusRequest(BaseModel):
    computer: str = Field(min_length=1, max_length=128)
    user: str | None = Field(default=None, max_length=256)
    ip: str | None = Field(default=None, max_length=64)
    timestamp: datetime | None = None

    @field_validator("computer", "user", "ip", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("computer")
    @classmethod
    def require_computer(cls, value: str | None) -> str:
        if not value:
            raise ValueError("Computer name is required.")
        return value

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ipaddress.ip_address(value)
        except ValueError as exc:
            raise ValueError("Invalid IP address.") from exc
        return value


class WorkstationStatusResponse(BaseModel):
    status: str
    computer: str
    sam_account_name: str | None = None
    received_at: datetime


class WorkstationUserStatus(BaseModel):
    computer_name: str
    ip_address: str | None = None
    received_at: datetime
    reported_at: datetime | None = None


class WorkstationLogonEvent(BaseModel):
    id: int
    received_at: datetime
    reported_at: datetime | None = None
    computer_name: str
    reported_user: str | None = None
    sam_account_name: str | None = None
    ip_address: str | None = None
    source: str


def normalize_sam_account_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if "\\" in normalized:
        normalized = normalized.rsplit("\\", 1)[-1]
    if "@" in normalized:
        normalized = normalized.split("@", 1)[0]
    normalized = normalized.strip()
    return normalized or None


def _require_workstation_token(header_token: str | None) -> None:
    settings = get_settings()
    expected_token = settings.workstation_status_token.get_secret_value()
    if not settings.workstation_status_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recebimento de status das estacoes esta desabilitado.",
        )
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WORKSTATION_STATUS_TOKEN nao esta configurado.",
        )
    if not header_token or not hmac.compare_digest(header_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token da estacao invalido.",
        )


def latest_workstation_status_for_users(
    sam_account_names: list[str | None],
) -> dict[str, WorkstationUserStatus]:
    names = sorted({name.lower() for name in sam_account_names if name})
    if not names:
        return {}
    settings = get_settings()
    if not settings.audit_database_enabled:
        return {}

    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ON (lower(sam_account_name))
                    lower(sam_account_name) AS normalized_user,
                    computer_name,
                    host(ip_address) AS ip_address,
                    received_at,
                    reported_at
                FROM workstation_status_events
                WHERE lower(sam_account_name) = ANY(%s)
                ORDER BY lower(sam_account_name), received_at DESC
                """,
                (names,),
            )
            rows = cursor.fetchall()

    return {
        row[0]: WorkstationUserStatus(
            computer_name=row[1],
            ip_address=row[2],
            received_at=row[3],
            reported_at=row[4],
        )
        for row in rows
    }


@router.get("/workstation-logons", response_model=list[WorkstationLogonEvent])
def list_workstation_logons(
    principal: Annotated[Principal, Depends(require_permission(Permission.read_users))],
    user: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    computer: Annotated[str | None, Query(min_length=2, max_length=128)] = None,
    ip: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[WorkstationLogonEvent]:
    settings = get_settings()
    if not settings.audit_database_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit database is disabled.",
        )

    clauses: list[str] = []
    params: list[Any] = []

    if user:
        search_value = f"%{user.strip().lower()}%"
        clauses.append(
            "(lower(coalesce(sam_account_name, '')) LIKE %s OR lower(coalesce(reported_user, '')) LIKE %s)"
        )
        params.extend([search_value, search_value])
    if computer:
        clauses.append("lower(computer_name) LIKE %s")
        params.append(f"%{computer.strip().lower()}%")
    if ip:
        clauses.append("host(ip_address) LIKE %s")
        params.append(f"%{ip.strip()}%")
    if start:
        clauses.append("received_at >= %s")
        params.append(start)
    if end:
        clauses.append("received_at <= %s")
        params.append(end)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        received_at,
                        reported_at,
                        computer_name,
                        reported_user,
                        sam_account_name,
                        host(ip_address) AS ip_address,
                        source
                    FROM workstation_status_events
                    {where_sql}
                    ORDER BY received_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                rows = cursor.fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nao foi possivel consultar logons das estacoes: {exc.__class__.__name__}",
        ) from exc

    audit_event(
        "workstation_logons_listed",
        operator=principal.subject,
        user_filter_present=bool(user),
        computer_filter_present=bool(computer),
        ip_filter_present=bool(ip),
        start_present=bool(start),
        end_present=bool(end),
        result_count=len(rows),
    )
    return [
        WorkstationLogonEvent(
            id=row[0],
            received_at=row[1],
            reported_at=row[2],
            computer_name=row[3],
            reported_user=row[4],
            sam_account_name=row[5],
            ip_address=row[6],
            source=row[7],
        )
        for row in rows
    ]


def _insert_workstation_status(payload: WorkstationStatusRequest) -> datetime:
    received_at = datetime.now(UTC)
    sam_account_name = normalize_sam_account_name(payload.user)
    raw_payload: dict[str, Any] = payload.model_dump(mode="json")

    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO workstation_status_events (
                    received_at, reported_at, computer_name, reported_user,
                    sam_account_name, ip_address, payload
                )
                VALUES (%s, %s, %s, %s, %s, %s::inet, %s::jsonb)
                """,
                (
                    received_at,
                    payload.timestamp,
                    payload.computer,
                    payload.user,
                    sam_account_name,
                    payload.ip,
                    json.dumps(raw_payload, default=str),
                ),
            )
        connection.commit()

    audit_event(
        "workstation_status_received",
        computer_name=payload.computer,
        sam_account_name=sam_account_name,
        ip_present=bool(payload.ip),
    )
    return received_at


@router.post("/workstation-status", response_model=WorkstationStatusResponse)
@router.post("/api/status", response_model=WorkstationStatusResponse)
def receive_workstation_status(
    payload: WorkstationStatusRequest,
    x_workstation_token: Annotated[str | None, Header(alias="X-Workstation-Token")] = None,
) -> WorkstationStatusResponse:
    _require_workstation_token(x_workstation_token)
    try:
        received_at = _insert_workstation_status(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nao foi possivel gravar status da estacao: {exc.__class__.__name__}",
        ) from exc
    return WorkstationStatusResponse(
        status="ok",
        computer=payload.computer,
        sam_account_name=normalize_sam_account_name(payload.user),
        received_at=received_at,
    )
