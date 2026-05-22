from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from ldap3 import MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel, Field, SecretStr

from app.ad_client import ad_connection
from app.ad_errors import ad_modify_error
from app.ad_utils import ACCOUNT_DISABLED_FLAG, ad_int, datetime_to_ad_timestamp, ldap_escape
from app.audit import audit_event
from app.config import get_settings
from app.guards import require_safe_write_transport
from app.security import Permission, Principal, require_permission
from app.users import USER_ATTRIBUTES, AdUser, _entry_to_user


router = APIRouter(prefix="/users", tags=["user-operations"])


class UserOperationType(StrEnum):
    enable = "enable"
    disable = "disable"
    unlock = "unlock"
    force_password_change = "force_password_change"
    reset_password = "reset_password"
    account_expiration = "account_expiration"


class UserOperationRequest(BaseModel):
    confirm: bool = Field(default=False)
    dry_run: bool = Field(default=True)
    reason: str = Field(min_length=8, max_length=500)


class ResetPasswordRequest(UserOperationRequest):
    new_password: SecretStr = Field(min_length=8, max_length=256)
    force_change_at_next_logon: bool = True


class AccountExpirationRequest(UserOperationRequest):
    never_expires: bool = True
    expires_at: datetime | None = None


class UserOperationResponse(BaseModel):
    operation: UserOperationType
    sam_account_name: str
    distinguished_name: str
    dry_run: bool
    changed: bool
    message: str
    before: AdUser
    after: AdUser | None = None


def _require_confirmation(request: UserOperationRequest) -> None:
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation requires confirm=true.",
        )


def _first(entry: dict[str, Any], name: str) -> Any:
    value = entry.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _get_user_entry(sam_account_name: str) -> tuple[str, dict[str, Any]]:
    settings = get_settings()
    escaped_login = ldap_escape(sam_account_name)
    search_filter = f"(&(objectCategory=person)(objectClass=user)(sAMAccountName={escaped_login}))"
    try:
        with ad_connection(settings) as connection:
            connection.search(
                search_base=settings.ad_base_dn,
                search_filter=search_filter,
                attributes=USER_ATTRIBUTES,
                size_limit=2,
            )
            if not connection.entries:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            entry = connection.entries[0].entry_attributes_as_dict
            distinguished_name = str(_first(entry, "distinguishedName") or "")
            return distinguished_name, entry
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory user lookup failed: {exc.__class__.__name__}",
        ) from exc


def _modify_user(dn: str, changes: dict[str, list[tuple[int, list[Any]]]]) -> None:
    settings = get_settings()
    try:
        with ad_connection(settings) as connection:
            if not connection.modify(dn, changes):
                raise ad_modify_error("Active Directory modify failed", connection.result)
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory modify failed: {exc.__class__.__name__}",
        ) from exc


def _operation_response(
    operation: UserOperationType,
    sam_account_name: str,
    dn: str,
    before: AdUser,
    dry_run: bool,
    changed: bool,
    message: str,
) -> UserOperationResponse:
    after = None
    if changed:
        _, after_entry = _get_user_entry(sam_account_name)
        after = _entry_to_user(after_entry)
    return UserOperationResponse(
        operation=operation,
        sam_account_name=sam_account_name,
        distinguished_name=dn,
        dry_run=dry_run,
        changed=changed,
        message=message,
        before=before,
        after=after,
    )


def _set_disabled_flag(current_uac: int, disabled: bool) -> int:
    if disabled:
        return current_uac | ACCOUNT_DISABLED_FLAG
    return current_uac & ~ACCOUNT_DISABLED_FLAG


def _run_simple_operation(
    sam_account_name: str,
    request: UserOperationRequest,
    principal: Principal,
    operation: UserOperationType,
    changes: dict[str, list[tuple[int, list[Any]]]],
) -> UserOperationResponse:
    _require_confirmation(request)
    dn, before_entry = _get_user_entry(sam_account_name)
    before = _entry_to_user(before_entry)

    changed = False
    if not request.dry_run:
        require_safe_write_transport()
        _modify_user(dn, changes)
        changed = True

    audit_event(
        "user_write_operation",
        operator=principal.subject,
        roles=[role.value for role in principal.roles],
        operation=operation.value,
        sam_account_name=sam_account_name,
        distinguished_name=dn,
        dry_run=request.dry_run,
        changed=changed,
        reason=request.reason,
    )
    return _operation_response(
        operation,
        sam_account_name,
        dn,
        before,
        request.dry_run,
        changed,
        "Dry run completed." if request.dry_run else "Operation completed.",
    )


@router.post("/{sam_account_name}/enable", response_model=UserOperationResponse)
def enable_user(
    sam_account_name: str,
    request: UserOperationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_users))],
) -> UserOperationResponse:
    _require_confirmation(request)
    _, before_entry = _get_user_entry(sam_account_name)
    current_uac = ad_int(_first(before_entry, "userAccountControl"))
    new_uac = _set_disabled_flag(current_uac, disabled=False)
    return _run_simple_operation(
        sam_account_name,
        request,
        principal,
        UserOperationType.enable,
        {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]},
    )


@router.post("/{sam_account_name}/disable", response_model=UserOperationResponse)
def disable_user(
    sam_account_name: str,
    request: UserOperationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_users))],
) -> UserOperationResponse:
    _require_confirmation(request)
    _, before_entry = _get_user_entry(sam_account_name)
    current_uac = ad_int(_first(before_entry, "userAccountControl"))
    new_uac = _set_disabled_flag(current_uac, disabled=True)
    return _run_simple_operation(
        sam_account_name,
        request,
        principal,
        UserOperationType.disable,
        {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]},
    )


@router.post("/{sam_account_name}/unlock", response_model=UserOperationResponse)
def unlock_user(
    sam_account_name: str,
    request: UserOperationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_users))],
) -> UserOperationResponse:
    return _run_simple_operation(
        sam_account_name,
        request,
        principal,
        UserOperationType.unlock,
        {"lockoutTime": [(MODIFY_REPLACE, [0])]},
    )


@router.post("/{sam_account_name}/force-password-change", response_model=UserOperationResponse)
def force_password_change(
    sam_account_name: str,
    request: UserOperationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_users))],
) -> UserOperationResponse:
    return _run_simple_operation(
        sam_account_name,
        request,
        principal,
        UserOperationType.force_password_change,
        {"pwdLastSet": [(MODIFY_REPLACE, [0])]},
    )


@router.post("/{sam_account_name}/reset-password", response_model=UserOperationResponse)
def reset_password(
    sam_account_name: str,
    request: ResetPasswordRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_users))],
) -> UserOperationResponse:
    _require_confirmation(request)
    settings = get_settings()
    if not settings.ad_use_ldaps and not request.dry_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset requires LDAPS when dry_run=false.",
        )

    dn, before_entry = _get_user_entry(sam_account_name)
    before = _entry_to_user(before_entry)
    encoded_password = f'"{request.new_password.get_secret_value()}"'.encode("utf-16-le")
    changes: dict[str, list[tuple[int, list[Any]]]] = {
        "unicodePwd": [(MODIFY_REPLACE, [encoded_password])]
    }
    if request.force_change_at_next_logon:
        changes["pwdLastSet"] = [(MODIFY_REPLACE, [0])]

    changed = False
    if not request.dry_run:
        require_safe_write_transport()
        _modify_user(dn, changes)
        changed = True

    audit_event(
        "user_write_operation",
        operator=principal.subject,
        roles=[role.value for role in principal.roles],
        operation=UserOperationType.reset_password.value,
        sam_account_name=sam_account_name,
        distinguished_name=dn,
        dry_run=request.dry_run,
        changed=changed,
        force_change_at_next_logon=request.force_change_at_next_logon,
        reason=request.reason,
    )
    return _operation_response(
        UserOperationType.reset_password,
        sam_account_name,
        dn,
        before,
        request.dry_run,
        changed,
        "Dry run completed." if request.dry_run else "Password reset completed.",
    )


@router.post("/{sam_account_name}/account-expiration", response_model=UserOperationResponse)
def set_account_expiration(
    sam_account_name: str,
    request: AccountExpirationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_users))],
) -> UserOperationResponse:
    _require_confirmation(request)
    account_expires = 0
    if not request.never_expires:
        if request.expires_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expires_at is required when never_expires=false.",
            )
        account_expires = datetime_to_ad_timestamp(request.expires_at)

    return _run_simple_operation(
        sam_account_name,
        request,
        principal,
        UserOperationType.account_expiration,
        {"accountExpires": [(MODIFY_REPLACE, [account_expires])]},
    )
