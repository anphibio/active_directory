from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel

from app.ad_client import ad_connection, paged_search
from app.ad_utils import ad_int, ad_timestamp_to_datetime, ldap_escape
from app.audit import audit_event
from app.config import get_settings
from app.security import Permission, Principal, require_permission


router = APIRouter(prefix="/groups", tags=["groups"])


GROUP_ATTRIBUTES = [
    "distinguishedName",
    "cn",
    "name",
    "sAMAccountName",
    "description",
    "mail",
    "managedBy",
    "member",
    "groupType",
    "whenCreated",
    "whenChanged",
]

MEMBER_ATTRIBUTES = [
    "distinguishedName",
    "objectClass",
    "sAMAccountName",
    "displayName",
    "cn",
    "mail",
]

USER_GROUP_LOOKUP_ATTRIBUTES = [
    "distinguishedName",
    "sAMAccountName",
    "userPrincipalName",
    "displayName",
    "memberOf",
]


class GroupStatus(StrEnum):
    all = "all"
    empty = "empty"
    with_members = "with_members"
    without_description = "without_description"
    without_owner = "without_owner"


class GroupMember(BaseModel):
    distinguished_name: str
    object_classes: list[str]
    sam_account_name: str | None = None
    display_name: str | None = None
    common_name: str | None = None
    email: str | None = None


class AdGroup(BaseModel):
    distinguished_name: str
    common_name: str | None = None
    name: str | None = None
    sam_account_name: str | None = None
    description: str | None = None
    email: str | None = None
    managed_by: str | None = None
    member_count: int
    group_type: int | None = None
    created_at: object | None = None
    changed_at: object | None = None


class GroupListResponse(BaseModel):
    items: list[AdGroup]
    count: int
    limit: int
    status: GroupStatus


class GroupMembersResponse(BaseModel):
    group: AdGroup
    members: list[GroupMember]
    count: int
    limit: int


class UserGroupsResponse(BaseModel):
    sam_account_name: str
    groups: list[AdGroup]
    count: int
    limit: int


def _first(entry: dict[str, object], name: str) -> object:
    value = entry.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _list(entry: dict[str, object], name: str) -> list[object]:
    value = entry.get(name)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _ranged_list(entry: dict[str, object], name: str) -> list[object]:
    values = _list(entry, name)
    range_prefix = f"{name};range="
    for key, value in entry.items():
        if key.startswith(range_prefix):
            values.extend(value if isinstance(value, list) else [value])
    return values


def _text(entry: dict[str, object], name: str) -> str | None:
    value = _first(entry, name)
    return str(value) if value not in (None, "") else None


def _entry_to_group(entry: dict[str, object]) -> AdGroup:
    members = _ranged_list(entry, "member")
    group_type = _first(entry, "groupType")
    return AdGroup(
        distinguished_name=_text(entry, "distinguishedName") or "",
        common_name=_text(entry, "cn"),
        name=_text(entry, "name"),
        sam_account_name=_text(entry, "sAMAccountName"),
        description=_text(entry, "description"),
        email=_text(entry, "mail"),
        managed_by=_text(entry, "managedBy"),
        member_count=len(members),
        group_type=ad_int(group_type) if group_type not in (None, "") else None,
        created_at=ad_timestamp_to_datetime(_first(entry, "whenCreated")),
        changed_at=ad_timestamp_to_datetime(_first(entry, "whenChanged")),
    )


def _entry_to_member(entry: dict[str, object]) -> GroupMember:
    return GroupMember(
        distinguished_name=_text(entry, "distinguishedName") or "",
        object_classes=[str(item) for item in _list(entry, "objectClass")],
        sam_account_name=_text(entry, "sAMAccountName"),
        display_name=_text(entry, "displayName"),
        common_name=_text(entry, "cn"),
        email=_text(entry, "mail"),
    )


def build_group_filter(status_filter: GroupStatus = GroupStatus.all, query: str | None = None) -> str:
    filters = ["(objectClass=group)"]

    if status_filter == GroupStatus.empty:
        filters.append("(!(member=*))")
    elif status_filter == GroupStatus.with_members:
        filters.append("(member=*)")
    elif status_filter == GroupStatus.without_description:
        filters.append("(!(description=*))")
    elif status_filter == GroupStatus.without_owner:
        filters.append("(!(managedBy=*))")

    if query:
        escaped_query = ldap_escape(query)
        filters.append(
            "(|"
            f"(cn=*{escaped_query}*)"
            f"(name=*{escaped_query}*)"
            f"(sAMAccountName=*{escaped_query}*)"
            f"(description=*{escaped_query}*)"
            ")"
        )

    return f"(&{''.join(filters)})"


def _query_groups(search_filter: str, limit: int, ou_dn: str | None = None) -> list[AdGroup]:
    settings = get_settings()
    try:
        with ad_connection(settings) as connection:
            entries = paged_search(
                connection,
                search_base=ou_dn or settings.ad_base_dn,
                search_filter=search_filter,
                attributes=GROUP_ATTRIBUTES,
                limit=limit,
            )
            return [_entry_to_group(entry) for entry in entries]
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory group query failed: {exc.__class__.__name__}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory connection failed: {exc.__class__.__name__}",
        ) from exc


def search_groups(status_filter: GroupStatus, query: str | None, limit: int, ou_dn: str | None = None) -> list[AdGroup]:
    return _query_groups(build_group_filter(status_filter, query), limit, ou_dn)


def get_group_by_identifier(identifier: str) -> AdGroup | None:
    escaped_identifier = ldap_escape(identifier)
    search_filter = (
        "(&"
        "(objectClass=group)"
        "(|"
        f"(cn={escaped_identifier})"
        f"(name={escaped_identifier})"
        f"(sAMAccountName={escaped_identifier})"
        f"(distinguishedName={escaped_identifier})"
        ")"
        ")"
    )
    groups = _query_groups(search_filter, 2)
    return groups[0] if groups else None


def _find_user_for_group_lookup(identifier: str) -> dict[str, object] | None:
    escaped_identifier = ldap_escape(identifier)
    search_filter = (
        "(&"
        "(objectCategory=person)"
        "(objectClass=user)"
        "(|"
        f"(sAMAccountName={escaped_identifier})"
        f"(userPrincipalName={escaped_identifier})"
        f"(distinguishedName={escaped_identifier})"
        ")"
        ")"
    )
    settings = get_settings()
    with ad_connection(settings) as connection:
        entries = paged_search(
            connection,
            search_base=settings.ad_base_dn,
            search_filter=search_filter,
            attributes=USER_GROUP_LOOKUP_ATTRIBUTES,
            limit=1,
        )
    return entries[0] if entries else None


def _resolve_user_group_dns(user_dn: str, direct_group_dns: list[str], include_nested: bool, limit: int) -> list[str]:
    group_dns = {str(group_dn) for group_dn in direct_group_dns if group_dn}
    if not include_nested or not user_dn or len(group_dns) >= limit:
        return sorted(group_dns)[:limit]

    settings = get_settings()
    search_filter = (
        "(&"
        "(objectClass=group)"
        f"(member:1.2.840.113556.1.4.1941:={ldap_escape(user_dn)})"
        ")"
    )
    with ad_connection(settings) as connection:
        entries = paged_search(
            connection,
            search_base=settings.ad_base_dn,
            search_filter=search_filter,
            attributes=["distinguishedName"],
            limit=limit,
        )
    for entry in entries:
        group_dn = _text(entry, "distinguishedName")
        if group_dn:
            group_dns.add(group_dn)
    return sorted(group_dns)[:limit]


@router.get("", response_model=GroupListResponse)
def list_groups(
    principal: Annotated[Principal, Depends(require_permission(Permission.read_groups))],
    status_filter: Annotated[GroupStatus, Query(alias="status")] = GroupStatus.all,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    ou_dn: Annotated[str | None, Query(max_length=500)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> GroupListResponse:
    groups = search_groups(status_filter, query, limit, ou_dn)
    audit_event(
        "groups_listed",
        operator=principal.subject,
        status=status_filter.value,
        query_present=bool(query),
        ou_filter_present=bool(ou_dn),
        result_count=len(groups),
    )
    return GroupListResponse(items=groups, count=len(groups), limit=limit, status=status_filter)


@router.get("/by-user/{sam_account_name}", response_model=UserGroupsResponse)
def list_groups_by_user(
    sam_account_name: str,
    principal: Annotated[Principal, Depends(require_permission(Permission.read_groups))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    include_nested: bool = True,
) -> UserGroupsResponse:
    try:
        user_entry = _find_user_for_group_lookup(sam_account_name)
        if user_entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        user_dn = _text(user_entry, "distinguishedName") or ""
        canonical_sam = _text(user_entry, "sAMAccountName") or sam_account_name
        group_dns = _resolve_user_group_dns(
            user_dn,
            [str(group_dn) for group_dn in _list(user_entry, "memberOf")],
            include_nested,
            limit,
        )
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory user group query failed: {exc.__class__.__name__}",
        ) from exc

    groups: list[AdGroup] = []
    for group_dn in group_dns:
        group = get_group_by_identifier(group_dn)
        if group is not None:
            groups.append(group)

    audit_event(
        "user_groups_listed",
        operator=principal.subject,
        sam_account_name=canonical_sam,
        include_nested=include_nested,
        result_count=len(groups),
    )
    return UserGroupsResponse(
        sam_account_name=canonical_sam,
        groups=groups,
        count=len(groups),
        limit=limit,
    )


@router.get("/{identifier}", response_model=AdGroup)
def get_group(
    identifier: str,
    principal: Annotated[Principal, Depends(require_permission(Permission.read_groups))],
) -> AdGroup:
    group = get_group_by_identifier(identifier)
    audit_event("group_lookup", operator=principal.subject, identifier=identifier, found=bool(group))
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    return group


@router.get("/{identifier}/members", response_model=GroupMembersResponse)
def list_group_members(
    identifier: str,
    principal: Annotated[Principal, Depends(require_permission(Permission.read_groups))],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> GroupMembersResponse:
    group = get_group_by_identifier(identifier)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    member_filter = f"(memberOf={ldap_escape(group.distinguished_name)})"
    settings = get_settings()
    try:
        with ad_connection(settings) as connection:
            connection.search(
                search_base=settings.ad_base_dn,
                search_filter=member_filter,
                attributes=MEMBER_ATTRIBUTES,
                size_limit=limit,
            )
            members = [_entry_to_member(entry.entry_attributes_as_dict) for entry in connection.entries]
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory member query failed: {exc.__class__.__name__}",
        ) from exc

    audit_event(
        "group_members_listed",
        operator=principal.subject,
        identifier=identifier,
        result_count=len(members),
    )
    return GroupMembersResponse(group=group, members=members, count=len(members), limit=limit)
