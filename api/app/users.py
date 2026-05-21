from datetime import UTC, datetime, timedelta
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel, Field
from typing import Annotated

from app.ad_client import ad_connection, paged_search
from app.ad_utils import (
    ACCOUNT_DISABLED_FLAG,
    LOCKOUT_FLAG,
    NEVER_EXPIRES_FLAG,
    ad_int,
    ad_timestamp_to_datetime,
    datetime_to_ad_timestamp,
    is_flag_set,
    ldap_escape,
)
from app.audit import audit_event
from app.config import get_settings
from app.security import Permission, Principal, require_permission
from app.workstation_status import latest_workstation_status_for_users


router = APIRouter(prefix="/users", tags=["users"])
ACCOUNT_NEVER_EXPIRES_VALUES = {0, 9223372036854775807}


USER_ATTRIBUTES = [
    "distinguishedName",
    "sAMAccountName",
    "userPrincipalName",
    "displayName",
    "givenName",
    "sn",
    "mail",
    "department",
    "title",
    "manager",
    "whenCreated",
    "whenChanged",
    "lastLogonTimestamp",
    "pwdLastSet",
    "msDS-UserPasswordExpiryTimeComputed",
    "accountExpires",
    "userAccountControl",
    "lockoutTime",
]


class UserStatus(StrEnum):
    all = "all"
    active = "active"
    disabled = "disabled"
    locked = "locked"
    inactive = "inactive"
    never_logged_on = "never_logged_on"
    password_never_expires = "password_never_expires"


class AdUser(BaseModel):
    distinguished_name: str
    sam_account_name: str | None = None
    user_principal_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    department: str | None = None
    title: str | None = None
    manager: str | None = None
    enabled: bool
    locked: bool
    password_never_expires: bool
    created_at: datetime | None = None
    changed_at: datetime | None = None
    last_logon_at: datetime | None = None
    password_last_set_at: datetime | None = None
    password_expires_at: datetime | None = None
    account_expires_at: datetime | None = None
    last_logon_computer: str | None = None
    last_logon_ip: str | None = None
    workstation_status_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[AdUser]
    count: int
    limit: int
    status: UserStatus


def _first(entry: dict[str, object], name: str) -> object:
    value = entry.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _text(entry: dict[str, object], name: str) -> str | None:
    value = _first(entry, name)
    return str(value) if value not in (None, "") else None


def _datetime(entry: dict[str, object], name: str) -> datetime | None:
    return ad_timestamp_to_datetime(_first(entry, name))


def _account_expires_datetime(entry: dict[str, object]) -> datetime | None:
    raw_value = _first(entry, "accountExpires")
    if isinstance(raw_value, datetime) and raw_value.year >= 9999:
        return None
    if isinstance(raw_value, str) and raw_value.startswith("9999-12-31"):
        return None
    account_expires = ad_int(raw_value, default=0)
    if account_expires in ACCOUNT_NEVER_EXPIRES_VALUES:
        return None
    return ad_timestamp_to_datetime(raw_value)


def _entry_to_user(entry: dict[str, object]) -> AdUser:
    user_account_control = ad_int(_first(entry, "userAccountControl"))
    lockout_time = ad_int(_first(entry, "lockoutTime"))
    return AdUser(
        distinguished_name=_text(entry, "distinguishedName") or "",
        sam_account_name=_text(entry, "sAMAccountName"),
        user_principal_name=_text(entry, "userPrincipalName"),
        display_name=_text(entry, "displayName"),
        email=_text(entry, "mail"),
        department=_text(entry, "department"),
        title=_text(entry, "title"),
        manager=_text(entry, "manager"),
        enabled=not is_flag_set(user_account_control, ACCOUNT_DISABLED_FLAG),
        locked=lockout_time > 0 or is_flag_set(user_account_control, LOCKOUT_FLAG),
        password_never_expires=is_flag_set(user_account_control, NEVER_EXPIRES_FLAG),
        created_at=_datetime(entry, "whenCreated"),
        changed_at=_datetime(entry, "whenChanged"),
        last_logon_at=_datetime(entry, "lastLogonTimestamp"),
        password_last_set_at=_datetime(entry, "pwdLastSet"),
        password_expires_at=(
            None
            if is_flag_set(user_account_control, NEVER_EXPIRES_FLAG)
            else _datetime(entry, "msDS-UserPasswordExpiryTimeComputed")
        ),
        account_expires_at=_account_expires_datetime(entry),
    )


def build_user_filter(
    status_filter: UserStatus = UserStatus.all,
    query: str | None = None,
    group_dn: str | None = None,
    inactive_days: int = 90,
) -> str:
    filters = ["(objectCategory=person)", "(objectClass=user)"]

    if status_filter == UserStatus.active:
        filters.append(f"(!(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG}))")
    elif status_filter == UserStatus.disabled:
        filters.append(f"(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG})")
    elif status_filter == UserStatus.locked:
        filters.append("(|(lockoutTime>=1)(userAccountControl:1.2.840.113556.1.4.803:=16))")
    elif status_filter == UserStatus.password_never_expires:
        filters.append(f"(userAccountControl:1.2.840.113556.1.4.803:={NEVER_EXPIRES_FLAG})")
    elif status_filter == UserStatus.never_logged_on:
        filters.append("(!(lastLogonTimestamp=*))")
    elif status_filter == UserStatus.inactive:
        cutoff = datetime_to_ad_timestamp(datetime.now(UTC) - timedelta(days=inactive_days))
        filters.append(f"(|(!(lastLogonTimestamp=*))(lastLogonTimestamp<={cutoff}))")

    if query:
        escaped_query = ldap_escape(query)
        filters.append(
            "(|"
            f"(sAMAccountName=*{escaped_query}*)"
            f"(userPrincipalName=*{escaped_query}*)"
            f"(displayName=*{escaped_query}*)"
            f"(mail=*{escaped_query}*)"
            ")"
        )

    if group_dn:
        filters.append(f"(memberOf={ldap_escape(group_dn)})")

    return f"(&{''.join(filters)})"


def search_users(
    status_filter: UserStatus,
    query: str | None,
    group_dn: str | None,
    inactive_days: int,
    limit: int,
    ou_dn: str | None = None,
) -> list[AdUser]:
    settings = get_settings()
    search_filter = build_user_filter(status_filter, query, group_dn, inactive_days)
    try:
        with ad_connection(settings) as connection:
            entries = paged_search(
                connection,
                search_base=ou_dn or settings.ad_base_dn,
                search_filter=search_filter,
                attributes=USER_ATTRIBUTES,
                limit=limit,
            )
            users = [_entry_to_user(entry) for entry in entries]
            try:
                statuses = latest_workstation_status_for_users(
                    [user.sam_account_name for user in users]
                )
            except Exception:
                statuses = {}
            for user in users:
                if not user.sam_account_name:
                    continue
                workstation_status = statuses.get(user.sam_account_name.lower())
                if not workstation_status:
                    continue
                user.last_logon_computer = workstation_status.computer_name
                user.last_logon_ip = workstation_status.ip_address
                user.workstation_status_at = workstation_status.received_at
            return users
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory query failed: {exc.__class__.__name__}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory connection failed: {exc.__class__.__name__}",
        ) from exc


@router.get("", response_model=UserListResponse)
def list_users(
    principal: Annotated[Principal, Depends(require_permission(Permission.read_users))],
    status_filter: Annotated[UserStatus, Query(alias="status")] = UserStatus.active,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    group_dn: Annotated[str | None, Query(max_length=500)] = None,
    ou_dn: Annotated[str | None, Query(max_length=500)] = None,
    inactive_days: Annotated[int, Query(ge=1, le=3650)] = 90,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> UserListResponse:
    users = search_users(status_filter, query, group_dn, inactive_days, limit, ou_dn)
    audit_event(
        "users_listed",
        operator=principal.subject,
        status=status_filter.value,
        query_present=bool(query),
        group_filter_present=bool(group_dn),
        ou_filter_present=bool(ou_dn),
        inactive_days=inactive_days,
        result_count=len(users),
    )
    return UserListResponse(items=users, count=len(users), limit=limit, status=status_filter)


@router.get("/{sam_account_name}", response_model=AdUser)
def get_user(
    sam_account_name: str,
    principal: Annotated[Principal, Depends(require_permission(Permission.read_users))],
) -> AdUser:
    users = search_users(
        status_filter=UserStatus.all,
        query=sam_account_name,
        group_dn=None,
        inactive_days=90,
        limit=10,
    )
    exact_match = next(
        (
            user
            for user in users
            if user.sam_account_name and user.sam_account_name.lower() == sam_account_name.lower()
        ),
        None,
    )
    audit_event(
        "user_lookup",
        operator=principal.subject,
        sam_account_name=sam_account_name,
        found=bool(exact_match),
    )
    if exact_match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return exact_match
