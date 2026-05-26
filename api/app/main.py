from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.ad_auth import authenticate_ad_user
from app.ad_client import test_ad_connection
from app.audit import AuditMiddleware, audit_event
from app.audit_routes import router as audit_router
from app.computer_operations import router as computer_operations_router
from app.computers import router as computers_router
from app.config import get_settings
from app.database import init_database
from app.group_operations import router as group_operations_router
from app.guards import validate_production_startup
from app.metrics import MetricsMiddleware, metrics_store
from app.security import (
    AdLoginRequest,
    AdLoginResponse,
    Permission,
    Principal,
    TokenRequest,
    TokenResponse,
    create_access_token,
    get_current_principal,
    require_bootstrap_token,
    require_permission,
)
from app.groups import router as groups_router
from app.reports import router as reports_router
from app.user_operations import router as user_operations_router
from app.users import router as users_router
from app.workstation_status import router as workstation_status_router

app = FastAPI(
    title="Active Directory Manager API",
    version="0.1.0",
    description="API para gerenciamento, auditoria e relatorios de Active Directory.",
)
settings = get_settings()
app.add_middleware(AuditMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Bootstrap-Token",
        "X-Correlation-ID",
        "X-Workstation-Token",
    ],
)
app.include_router(audit_router)
app.include_router(computer_operations_router)
app.include_router(computers_router)
app.include_router(group_operations_router)
app.include_router(groups_router)
app.include_router(reports_router)
app.include_router(user_operations_router)
app.include_router(users_router)
app.include_router(workstation_status_router)


@app.on_event("startup")
def startup() -> None:
    validate_production_startup()
    init_database()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Active Directory Manager API",
        "status": "running",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=metrics_store.prometheus(), media_type="text/plain; version=0.0.4")


@app.post("/auth/token")
def issue_token(
    token_request: TokenRequest,
    _: Annotated[None, Depends(require_bootstrap_token)],
) -> TokenResponse:
    token = create_access_token(token_request.subject, token_request.roles)
    audit_event(
        "auth_token_issued",
        subject=token_request.subject,
        roles=[role.value for role in token_request.roles],
    )
    return token


@app.post("/auth/ad-login", response_model=AdLoginResponse)
def ad_login(login_request: AdLoginRequest) -> AdLoginResponse:
    ad_user = authenticate_ad_user(login_request.username, login_request.password)
    token = create_access_token(ad_user.subject, ad_user.roles, ad_user.member_dns)
    audit_event(
        "ad_login_success",
        operator=ad_user.subject,
        distinguished_name=ad_user.distinguished_name,
        roles=[role.value for role in ad_user.roles],
        authorization_groups=ad_user.member_dns,
        group_count=len(ad_user.member_dns),
    )
    return AdLoginResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_at=token.expires_at,
        roles=token.roles,
        subject=ad_user.subject,
        display_name=ad_user.display_name,
        email=ad_user.email,
    )


@app.get("/auth/me")
def whoami(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    return principal


@app.get("/config/summary")
def config_summary(
    _: Annotated[Principal, Depends(require_permission(Permission.read_config))],
) -> dict[str, str | bool | int | list[str]]:
    settings = get_settings()
    return settings.safe_summary()


@app.get("/config/runtime")
def config_runtime() -> dict[str, str | bool]:
    settings = get_settings()
    is_production = settings.app_env.lower() == "production"
    return {
        "app_env": settings.app_env,
        "is_production": is_production,
        "operation_simulation_enabled": not is_production,
    }


@app.get("/ad/connection-test")
def ad_connection_test(
    principal: Annotated[Principal, Depends(require_permission(Permission.test_ad_connection))],
) -> dict[str, str | bool]:
    result = test_ad_connection(get_settings())
    audit_event(
        "ad_connection_test",
        operator=principal.subject,
        result_status=result.status,
        bind_successful=result.bind_successful,
    )
    return {
        "status": result.status,
        "server": result.server,
        "use_ldaps": result.use_ldaps,
        "bind_successful": result.bind_successful,
        "message": result.message,
    }
