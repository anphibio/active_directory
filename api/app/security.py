import base64
import hashlib
import hmac
import json
import time
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.config import get_settings


class Role(StrEnum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"
    auditor = "auditor"


class Permission(StrEnum):
    read_config = "read:config"
    test_ad_connection = "test:ad_connection"
    read_users = "read:users"
    read_groups = "read:groups"
    read_computers = "read:computers"
    run_reports = "run:reports"
    write_users = "write:users"
    write_groups = "write:groups"
    write_computers = "write:computers"
    read_audit = "read:audit"
    administer = "administer"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.viewer: {
        Permission.read_users,
        Permission.read_groups,
        Permission.read_computers,
        Permission.run_reports,
    },
    Role.operator: {
        Permission.read_users,
        Permission.read_groups,
        Permission.read_computers,
        Permission.run_reports,
        Permission.write_users,
        Permission.write_groups,
        Permission.write_computers,
        Permission.test_ad_connection,
    },
    Role.admin: set(Permission),
    Role.auditor: {
        Permission.read_users,
        Permission.read_groups,
        Permission.read_computers,
        Permission.run_reports,
        Permission.read_audit,
    },
}


class TokenRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=120)
    roles: list[Role] = Field(default=[Role.viewer], min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    roles: list[Role]


class AdLoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=1, max_length=512)


class AdLoginResponse(TokenResponse):
    subject: str
    display_name: str | None = None
    email: str | None = None


class Principal(BaseModel):
    subject: str
    roles: list[Role]
    permissions: list[Permission]
    expires_at: int
    authorization_groups: list[str] = Field(default_factory=list)


bearer_scheme = HTTPBearer(auto_error=False)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(data: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def permissions_for_roles(roles: list[Role]) -> list[Permission]:
    permissions: set[Permission] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS[role])
    return sorted(permissions, key=str)


def create_access_token(
    subject: str,
    roles: list[Role],
    authorization_groups: list[str] | None = None,
) -> TokenResponse:
    settings = get_settings()
    secret = settings.jwt_secret.get_secret_value()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured.",
        )

    expires_at = int(time.time()) + settings.access_token_expire_minutes * 60
    payload = {
        "sub": subject,
        "roles": [role.value for role in roles],
        "authorization_groups": authorization_groups or [],
        "exp": expires_at,
        "iat": int(time.time()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = _sign(signing_input, secret)
    return TokenResponse(
        access_token=f"{signing_input}.{signature}",
        expires_at=expires_at,
        roles=roles,
    )


def decode_access_token(token: str) -> Principal:
    settings = get_settings()
    secret = settings.jwt_secret.get_secret_value()
    try:
        encoded_header, encoded_payload, signature = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = _sign(signing_input, secret)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    try:
        payload = json.loads(_b64decode(encoded_payload))
        expires_at = int(payload["exp"])
        roles = [Role(role) for role in payload["roles"]]
        subject = str(payload["sub"])
        authorization_groups = [
            str(group_dn) for group_dn in payload.get("authorization_groups", []) if group_dn
        ]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    if expires_at < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")

    return Principal(
        subject=subject,
        roles=roles,
        permissions=permissions_for_roles(roles),
        expires_at=expires_at,
        authorization_groups=authorization_groups,
    )


def require_bootstrap_token(
    x_bootstrap_token: Annotated[str | None, Header(alias="X-Bootstrap-Token")] = None,
) -> None:
    expected_token = get_settings().app_bootstrap_admin_token.get_secret_value()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APP_BOOTSTRAP_ADMIN_TOKEN is not configured.",
        )
    if not x_bootstrap_token or not hmac.compare_digest(x_bootstrap_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bootstrap token.")


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    principal = decode_access_token(credentials.credentials)
    from app.audit import set_audit_actor

    set_audit_actor(
        principal.subject,
        [role.value for role in principal.roles],
        principal.authorization_groups,
    )
    return principal


def require_permission(permission: Permission):
    def dependency(principal: Annotated[Principal, Depends(get_current_principal)]) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
        return principal

    return dependency
