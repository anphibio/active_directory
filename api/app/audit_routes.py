from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.config import get_settings
from app.database import database_connection
from app.security import Permission, Principal, require_permission


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEvent(BaseModel):
    id: int
    occurred_at: datetime
    event: str
    operator: str | None = None
    target: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any]


@router.get("/events", response_model=list[AuditEvent])
def list_audit_events(
    _: Annotated[Principal, Depends(require_permission(Permission.read_audit))],
    event: Annotated[str | None, Query(max_length=120)] = None,
    events: Annotated[str | None, Query(max_length=500)] = None,
    operation: Annotated[str | None, Query(max_length=120)] = None,
    operator: Annotated[str | None, Query(max_length=120)] = None,
    target: Annotated[str | None, Query(max_length=500)] = None,
    correlation_id: Annotated[str | None, Query(max_length=120)] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEvent]:
    if not get_settings().audit_database_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit database is disabled.",
        )

    clauses: list[str] = []
    params: list[Any] = []

    if event:
        clauses.append("event = %s")
        params.append(event)
    if events:
        event_names = [name.strip() for name in events.split(",") if name.strip()]
        if event_names:
            event_names = event_names[:20]
            placeholders = ", ".join(["%s"] * len(event_names))
            clauses.append(f"event IN ({placeholders})")
            params.extend(event_names)
    if operation:
        clauses.append("payload ->> 'operation' = %s")
        params.append(operation)
    if operator:
        clauses.append("operator = %s")
        params.append(operator)
    if target:
        clauses.append("target ILIKE %s")
        params.append(f"%{target}%")
    if correlation_id:
        clauses.append("correlation_id = %s")
        params.append(correlation_id)
    if q:
        clauses.append("(event ILIKE %s OR operator ILIKE %s OR target ILIKE %s OR payload::text ILIKE %s)")
        search_value = f"%{q}%"
        params.extend([search_value, search_value, search_value, search_value])
    if start:
        clauses.append("occurred_at >= %s")
        params.append(start)
    if end:
        clauses.append("occurred_at <= %s")
        params.append(end)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, occurred_at, event, operator, target, correlation_id, payload
                    FROM audit_events
                    {where_sql}
                    ORDER BY occurred_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                rows = cursor.fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Audit database query failed: {exc.__class__.__name__}",
        ) from exc

    return [
        AuditEvent(
            id=row[0],
            occurred_at=row[1],
            event=row[2],
            operator=row[3],
            target=row[4],
            correlation_id=row[5],
            payload=row[6] or {},
        )
        for row in rows
    ]
