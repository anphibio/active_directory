from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from ldap3 import MODIFY_ADD, MODIFY_DELETE
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel, Field

from app.ad_client import ad_connection
from app.ad_errors import ad_modify_error
from app.audit import audit_event
from app.config import get_settings
from app.guards import require_safe_write_transport
from app.groups import AdGroup, get_group_by_identifier
from app.security import Permission, Principal, require_permission
from app.user_operations import _get_user_entry


router = APIRouter(prefix="/groups", tags=["group-operations"])


class GroupOperationType(StrEnum):
    add_member = "add_member"
    remove_member = "remove_member"


class GroupMembershipRequest(BaseModel):
    sam_account_name: str = Field(min_length=1, max_length=120)
    confirm: bool = False
    dry_run: bool = True
    reason: str = Field(min_length=8, max_length=500)
    protected_group_confirm: bool = False


class GroupOperationResponse(BaseModel):
    operation: GroupOperationType
    group: AdGroup
    sam_account_name: str
    user_distinguished_name: str
    dry_run: bool
    changed: bool
    protected_group: bool
    message: str


def _require_confirmation(request: GroupMembershipRequest) -> None:
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation requires confirm=true.",
        )


def _is_protected_group(group: AdGroup) -> bool:
    settings = get_settings()
    candidates = [
        group.common_name or "",
        group.name or "",
        group.sam_account_name or "",
        group.distinguished_name,
    ]
    lowered_candidates = [candidate.lower() for candidate in candidates]
    return any(
        pattern in candidate
        for pattern in settings.protected_groups()
        for candidate in lowered_candidates
    )


def _require_protected_confirmation(request: GroupMembershipRequest, group: AdGroup) -> bool:
    protected = _is_protected_group(group)
    if protected and not request.protected_group_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Protected group operation requires protected_group_confirm=true.",
        )
    return protected


def _modify_group_member(group_dn: str, user_dn: str, operation: GroupOperationType) -> None:
    modify_operation = MODIFY_ADD if operation == GroupOperationType.add_member else MODIFY_DELETE
    try:
        with ad_connection(get_settings()) as connection:
            if not connection.modify(group_dn, {"member": [(modify_operation, [user_dn])]}):
                raise ad_modify_error("Active Directory group modify failed", connection.result)
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory group modify failed: {exc.__class__.__name__}",
        ) from exc


def _run_membership_operation(
    identifier: str,
    request: GroupMembershipRequest,
    principal: Principal,
    operation: GroupOperationType,
) -> GroupOperationResponse:
    _require_confirmation(request)
    group = get_group_by_identifier(identifier)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    protected = _require_protected_confirmation(request, group)
    user_dn, _ = _get_user_entry(request.sam_account_name)

    changed = False
    if not request.dry_run:
        require_safe_write_transport()
        _modify_group_member(group.distinguished_name, user_dn, operation)
        changed = True

    audit_event(
        "group_write_operation",
        operator=principal.subject,
        roles=[role.value for role in principal.roles],
        operation=operation.value,
        group=group.common_name or group.sam_account_name or group.name,
        group_sam_account_name=group.sam_account_name,
        group_dn=group.distinguished_name,
        sam_account_name=request.sam_account_name,
        user_dn=user_dn,
        protected_group=protected,
        dry_run=request.dry_run,
        changed=changed,
        reason=request.reason,
    )
    return GroupOperationResponse(
        operation=operation,
        group=group,
        sam_account_name=request.sam_account_name,
        user_distinguished_name=user_dn,
        dry_run=request.dry_run,
        changed=changed,
        protected_group=protected,
        message="Dry run completed." if request.dry_run else "Operation completed.",
    )


@router.post("/{identifier}/members/add", response_model=GroupOperationResponse)
def add_group_member(
    identifier: str,
    request: GroupMembershipRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_groups))],
) -> GroupOperationResponse:
    return _run_membership_operation(identifier, request, principal, GroupOperationType.add_member)


@router.post("/{identifier}/members/remove", response_model=GroupOperationResponse)
def remove_group_member(
    identifier: str,
    request: GroupMembershipRequest,
    principal: Annotated[Principal, Depends(require_permission(Permission.write_groups))],
) -> GroupOperationResponse:
    return _run_membership_operation(identifier, request, principal, GroupOperationType.remove_member)
