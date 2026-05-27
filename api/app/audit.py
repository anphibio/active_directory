import json
from ipaddress import ip_address, ip_network
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


def _is_trusted_proxy(client_host: str | None) -> bool:
    if not client_host:
        return False

    try:
        client_ip = ip_address(client_host)
    except ValueError:
        return False

    for network_value in get_settings().trusted_proxy_networks():
        try:
            if client_ip in ip_network(network_value, strict=False):
                return True
        except ValueError:
            continue
    return False


def _first_forwarded_ip(value: str | None) -> str | None:
    if not value:
        return None
    for candidate in value.split(","):
        candidate = candidate.strip()
        try:
            return str(ip_address(candidate))
        except ValueError:
            continue
    return None


def client_origin_from_request(request: Request) -> str:
    direct_host = request.client.host if request.client else None
    if not _is_trusted_proxy(direct_host):
        return direct_host or "unknown"

    forwarded_for = _first_forwarded_ip(request.headers.get("X-Forwarded-For"))
    if forwarded_for:
        return forwarded_for

    real_ip = _first_forwarded_ip(request.headers.get("X-Real-IP"))
    if real_ip:
        return real_ip

    return direct_host or "unknown"


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
                "origin": client_origin_from_request(request),
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
