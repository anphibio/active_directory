import json
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings
from app.metrics import metrics_store


AUDIT_ACTOR: ContextVar[dict[str, Any] | None] = ContextVar("AUDIT_ACTOR", default=None)
AUDIT_REQUEST: ContextVar[dict[str, Any] | None] = ContextVar("AUDIT_REQUEST", default=None)


SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "authorization",
    "x-bootstrap-token",
    "ad_bind_password",
}


def set_audit_actor(subject: str, roles: list[str], authorization_groups: list[str]) -> None:
    AUDIT_ACTOR.set(
        {
            "operator": subject,
            "roles": roles,
            "authorization_groups": authorization_groups,
        }
    )


def new_correlation_id() -> str:
    return str(uuid4())


def mask_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(sensitive in lowered for sensitive in SENSITIVE_KEYS):
        return "***"
    return value


def audit_event(event: str, **fields: Any) -> None:
    metrics_store.record_event(event)
    actor = AUDIT_ACTOR.get() or {}
    request_context = AUDIT_REQUEST.get() or {}
    enriched_fields = {
        **request_context,
        **actor,
        **fields,
    }
    safe_fields = {key: mask_value(key, value) for key, value in enriched_fields.items()}
    occurred_at = datetime.now(UTC)
    payload = {
        "timestamp": occurred_at.isoformat(),
        "event": event,
        **safe_fields,
    }
    print(json.dumps(payload, default=str), flush=True)
    persist_audit_event(event, occurred_at, safe_fields)


def _target_from_fields(fields: dict[str, Any]) -> str | None:
    for key in (
        "distinguished_name",
        "group_dn",
        "user_dn",
        "sam_account_name",
        "identifier",
        "path",
    ):
        value = fields.get(key)
        if value:
            return str(value)
    return None


def persist_audit_event(event: str, occurred_at: datetime, fields: dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.audit_database_enabled:
        return

    try:
        from app.database import database_connection

        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events (
                        occurred_at, event, operator, target, correlation_id, payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        occurred_at,
                        event,
                        fields.get("operator"),
                        _target_from_fields(fields),
                        fields.get("correlation_id"),
                        json.dumps(fields, default=str),
                    ),
                )
            connection.commit()
    except Exception as exc:
        fallback = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": "audit_persist_failed",
            "error": exc.__class__.__name__,
            "original_event": event,
        }
        print(json.dumps(fallback), flush=True)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or new_correlation_id()
        request.state.correlation_id = correlation_id
        request_token = AUDIT_REQUEST.set(
            {
                "correlation_id": correlation_id,
                "origin": request.client.host if request.client else "unknown",
                "path": request.url.path,
            }
        )
        actor_token = AUDIT_ACTOR.set(None)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id

            audit_event(
                "http_request",
                method=request.method,
                status_code=response.status_code,
            )
            return response
        finally:
            AUDIT_ACTOR.reset(actor_token)
            AUDIT_REQUEST.reset(request_token)
