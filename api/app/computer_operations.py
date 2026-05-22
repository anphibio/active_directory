from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from ldap3 import MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel, Field

from app.ad_client import ad_connection
from app.ad_errors import ad_modify_error
from app.ad_utils import ACCOUNT_DISABLED_FLAG, ad_int, ldap_escape
from app.audit import audit_event
from app.computers import COMPUTER_ATTRIBUTES, AdComputer, _entry_to_computer
from app.config import get_settings
from app.guards import require_safe_write_transport
from app.security import Permission, Principal, require_permission


router = APIRouter(prefix="/computers", tags=["computer-operations"])


class ComputerOperationType(StrEnum):
    enable = "enable"
    disable = "disable"
    update_metadata = "update_metadata"


class ComputerOperationRequest(BaseModel):
    confirm: bool = False
    dry_run: bool = True
    reason: str = Field(min_length=8, max_length=500)


class ComputerMetadataRequest(ComputerOperationRequest):
    description: str | None = Field(default=None, max_length=1024)
    location: str | None = Field(default=None, max_length=512)
    managed_by: str | None = Field(default=None, max_length=500)


class ComputerOperationResponse(BaseModel):
    operation: ComputerOperationType
    identifier: str
    distinguished_name: str
    dry_run: bool
    changed: bool
    message: str
    before: AdComputer
    after: AdComputer | None = None


def _require_confirmation(request: ComputerOperationRequest) -> None:
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


def _get_computer_entry(identifier: str) -> tuple[str, dict[str, Any]]:
    settings = get_settings()
    escaped_identifier = ldap_escape(identifier)
    search_filter = (
        "(&"
        "(objectCategory=computer)"
        "(|"
        f"(cn={escaped_identifier})"
        f"(name={escaped_identifier})"
        f"(dNSHostName={escaped_identifier})"
        f"(sAMAccountName={escaped_identifier})"
        f"(distinguishedName={escaped_identifier})"
        ")"
        ")"
    )
    try:
        with ad_connection(settings) as connection:
            connection.search(
                search_base=settings.ad_base_dn,
                search_filter=search_filter,
                attributes=COMPUTER_ATTRIBUTES,
                size_limit=2,
            )
            if not connection.entries:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer not found.")
            entry = connection.entries[0].entry_attributes_as_dict
            distinguished_name = str(_first(entry, "distinguishedName") or "")
            return distinguished_name, entry
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory computer lookup failed: {exc.__class__.__name__}",
        ) from exc


def _modify_computer(dn: str, changes: dict[str, list[tuple[int, list[Any]]]]) -> None:
    try:
        with ad_connection(get_settings()) as connection:
            if not connection.modify(dn, changes):
                raise ad_modify_error("Active Directory computer modify failed", connection.result)
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory computer modify failed: {exc.__class__.__name__}",
        ) from exc


def _operation_response(
    operation: ComputerOperationType,
    identifier: str,
    dn: str,
    before: AdComputer,
    dry_run: bool,
    changed: bool,
    message: str,
) -> ComputerOperationResponse:
    after = None
    if changed:
        _, after_entry = _get_computer_entry(identifier)
        after = _entry_to_computer(after_entry)
    return ComputerOperationResponse(
        operation=operation,
        identifier=identifier,
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


def _run_computer_operation(
    identifier: str,
    request: ComputerOperationRequest,
    principal: Principal,
    operation: ComputerOperationType,
    changes: dict[str, list[tuple[int, list[Any]]]],
) -> ComputerOperationResponse:
    _require_confirmation(request)
    dn, before_entry = _get_computer_entry(identifier)
    before = _entry_to_computer(before_entry)

    changed = False
    if not request.dry_run:
        require_safe_write_transport()
        _modify_computer(dn, changes)
        changed = True

    audit_event(
        "computer_write_operation",
        operator=principal.subject,
        roles=[role.value for role in principal.roles],
        operation=operation.value,
        identifier=identifier,
        distinguished_name=dn,
        dry_run=request.dry_run,
        changed=changed,
        reason=request.reason,
    )
    return _operation_response(
        operation,
        identifier,
        dn,
        before,
        request.dry_run,
        changed,
        "Dry run completed." if request.dry_run else "Operation completed.",
    )


@router.post("/{identifier}/enable", response_model=ComputerOperationResponse)
def enable_computer(
    identifier: str,
    request: ComputerOperationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_computers))],
) -> ComputerOperationResponse:
    _require_confirmation(request)
    _, before_entry = _get_computer_entry(identifier)
    current_uac = ad_int(_first(before_entry, "userAccountControl"))
    new_uac = _set_disabled_flag(current_uac, disabled=False)
    return _run_computer_operation(
        identifier,
        request,
        principal,
        ComputerOperationType.enable,
        {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]},
    )


@router.post("/{identifier}/disable", response_model=ComputerOperationResponse)
def disable_computer(
    identifier: str,
    request: ComputerOperationRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_computers))],
) -> ComputerOperationResponse:
    _require_confirmation(request)
    _, before_entry = _get_computer_entry(identifier)
    current_uac = ad_int(_first(before_entry, "userAccountControl"))
    new_uac = _set_disabled_flag(current_uac, disabled=True)
    return _run_computer_operation(
        identifier,
        request,
        principal,
        ComputerOperationType.disable,
        {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]},
    )


@router.post("/{identifier}/metadata", response_model=ComputerOperationResponse)
def update_computer_metadata(
    identifier: str,
    request: ComputerMetadataRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_computers))],
) -> ComputerOperationResponse:
    changes: dict[str, list[tuple[int, list[Any]]]] = {}
    if request.description is not None:
        changes["description"] = [(MODIFY_REPLACE, [request.description])]
    if request.location is not None:
        changes["location"] = [(MODIFY_REPLACE, [request.location])]
    if request.managed_by is not None:
        changes["managedBy"] = [(MODIFY_REPLACE, [request.managed_by])]

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one metadata field must be provided.",
        )

    return _run_computer_operation(
        identifier,
        request,
        principal,
        ComputerOperationType.update_metadata,
        changes,
    )
