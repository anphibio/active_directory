import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.security import Permission, Role, create_access_token, decode_access_token, require_permission


def test_created_token_contains_role_permissions(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()

    token = create_access_token("tester", [Role.viewer])
    principal = decode_access_token(token.access_token)

    assert principal.subject == "tester"
    assert Permission.read_users in principal.permissions
    assert Permission.write_users not in principal.permissions


def test_permission_dependency_rejects_missing_permission(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    principal = decode_access_token(create_access_token("tester", [Role.viewer]).access_token)

    dependency = require_permission(Permission.write_users)

    with pytest.raises(HTTPException):
        dependency(principal)


def test_permission_dependency_accepts_admin(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    principal = decode_access_token(create_access_token("admin", [Role.admin]).access_token)

    dependency = require_permission(Permission.write_users)

    assert dependency(principal) == principal
