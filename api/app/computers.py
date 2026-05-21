from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from ldap3.core.exceptions import LDAPException
from pydantic import BaseModel

from app.ad_client import ad_connection, paged_search
from app.ad_utils import (
    ACCOUNT_DISABLED_FLAG,
    SERVER_TRUST_ACCOUNT_FLAG,
    WORKSTATION_TRUST_ACCOUNT_FLAG,
    ad_int,
    ad_timestamp_to_datetime,
    datetime_to_ad_timestamp,
    is_flag_set,
    ldap_escape,
)
from app.audit import audit_event
from app.config import get_settings
from app.security import Permission, Principal, require_permission


router = APIRouter(prefix="/computers", tags=["computers"])


COMPUTER_ATTRIBUTES = [
    "distinguishedName",
    "cn",
    "name",
    "dNSHostName",
    "sAMAccountName",
    "description",
    "location",
    "managedBy",
    "operatingSystem",
    "operatingSystemVersion",
    "operatingSystemServicePack",
    "lastLogonTimestamp",
    "pwdLastSet",
    "userAccountControl",
    "whenCreated",
    "whenChanged",
]


class ComputerStatus(StrEnum):
    all = "all"
    active = "active"
    disabled = "disabled"
    inactive = "inactive"
    never_logged_on = "never_logged_on"
    servers = "servers"
    workstations = "workstations"
    domain_controllers = "domain_controllers"
    old_machine_password = "old_machine_password"
    missing_metadata = "missing_metadata"


class AdComputer(BaseModel):
    distinguished_name: str
    common_name: str | None = None
    name: str | None = None
    dns_hostname: str | None = None
    sam_account_name: str | None = None
    description: str | None = None
    location: str | None = None
    managed_by: str | None = None
    operating_system: str | None = None
    operating_system_version: str | None = None
    operating_system_service_pack: str | None = None
    enabled: bool
    is_server: bool
    is_workstation: bool
    is_domain_controller: bool
    created_at: datetime | None = None
    changed_at: datetime | None = None
    last_logon_at: datetime | None = None
    password_last_set_at: datetime | None = None


class ComputerListResponse(BaseModel):
    items: list[AdComputer]
    count: int
    limit: int
    status: ComputerStatus


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


def _entry_to_computer(entry: dict[str, object]) -> AdComputer:
    user_account_control = ad_int(_first(entry, "userAccountControl"))
    return AdComputer(
        distinguished_name=_text(entry, "distinguishedName") or "",
        common_name=_text(entry, "cn"),
        name=_text(entry, "name"),
        dns_hostname=_text(entry, "dNSHostName"),
        sam_account_name=_text(entry, "sAMAccountName"),
        description=_text(entry, "description"),
        location=_text(entry, "location"),
        managed_by=_text(entry, "managedBy"),
        operating_system=_text(entry, "operatingSystem"),
        operating_system_version=_text(entry, "operatingSystemVersion"),
        operating_system_service_pack=_text(entry, "operatingSystemServicePack"),
        enabled=not is_flag_set(user_account_control, ACCOUNT_DISABLED_FLAG),
        is_server=is_flag_set(user_account_control, SERVER_TRUST_ACCOUNT_FLAG),
        is_workstation=is_flag_set(user_account_control, WORKSTATION_TRUST_ACCOUNT_FLAG),
        is_domain_controller=is_flag_set(user_account_control, SERVER_TRUST_ACCOUNT_FLAG),
        created_at=_datetime(entry, "whenCreated"),
        changed_at=_datetime(entry, "whenChanged"),
        last_logon_at=_datetime(entry, "lastLogonTimestamp"),
        password_last_set_at=_datetime(entry, "pwdLastSet"),
    )


def build_computer_filter(
    status_filter: ComputerStatus = ComputerStatus.active,
    query: str | None = None,
    ou_dn: str | None = None,
    operating_system: str | None = None,
    inactive_days: int = 90,
    machine_password_days: int = 90,
) -> tuple[str, str | None]:
    filters = ["(objectCategory=computer)"]
    search_base = ou_dn

    if status_filter == ComputerStatus.active:
        filters.append(f"(!(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG}))")
    elif status_filter == ComputerStatus.disabled:
        filters.append(f"(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG})")
    elif status_filter == ComputerStatus.inactive:
        cutoff = datetime_to_ad_timestamp(datetime.now(UTC) - timedelta(days=inactive_days))
        filters.append(f"(|(!(lastLogonTimestamp=*))(lastLogonTimestamp<={cutoff}))")
    elif status_filter == ComputerStatus.never_logged_on:
        filters.append("(!(lastLogonTimestamp=*))")
    elif status_filter == ComputerStatus.servers:
        filters.append(f"(userAccountControl:1.2.840.113556.1.4.803:={SERVER_TRUST_ACCOUNT_FLAG})")
    elif status_filter == ComputerStatus.workstations:
        filters.append(
            f"(userAccountControl:1.2.840.113556.1.4.803:={WORKSTATION_TRUST_ACCOUNT_FLAG})"
        )
    elif status_filter == ComputerStatus.domain_controllers:
        filters.append(f"(userAccountControl:1.2.840.113556.1.4.803:={SERVER_TRUST_ACCOUNT_FLAG})")
    elif status_filter == ComputerStatus.old_machine_password:
        cutoff = datetime_to_ad_timestamp(datetime.now(UTC) - timedelta(days=machine_password_days))
        filters.append(f"(|(!(pwdLastSet=*))(pwdLastSet<={cutoff}))")
    elif status_filter == ComputerStatus.missing_metadata:
        filters.append("(|(!(description=*))(!(location=*))(!(managedBy=*)))")

    if query:
        escaped_query = ldap_escape(query)
        filters.append(
            "(|"
            f"(cn=*{escaped_query}*)"
            f"(name=*{escaped_query}*)"
            f"(dNSHostName=*{escaped_query}*)"
            f"(sAMAccountName=*{escaped_query}*)"
            f"(operatingSystem=*{escaped_query}*)"
            ")"
        )

    if operating_system:
        filters.append(f"(operatingSystem=*{ldap_escape(operating_system)}*)")

    return f"(&{''.join(filters)})", search_base


def search_computers(
    status_filter: ComputerStatus,
    query: str | None,
    ou_dn: str | None,
    operating_system: str | None,
    inactive_days: int,
    machine_password_days: int,
    limit: int,
) -> list[AdComputer]:
    settings = get_settings()
    search_filter, search_base_override = build_computer_filter(
        status_filter,
        query,
        ou_dn,
        operating_system,
        inactive_days,
        machine_password_days,
    )
    try:
        with ad_connection(settings) as connection:
            entries = paged_search(
                connection,
                search_base=search_base_override or settings.ad_base_dn,
                search_filter=search_filter,
                attributes=COMPUTER_ATTRIBUTES,
                limit=limit,
            )
            return [_entry_to_computer(entry) for entry in entries]
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory computer query failed: {exc.__class__.__name__}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory connection failed: {exc.__class__.__name__}",
        ) from exc


@router.get("", response_model=ComputerListResponse)
def list_computers(
    principal: Annotated[Principal, Depends(require_permission(Permission.read_computers))],
    status_filter: Annotated[ComputerStatus, Query(alias="status")] = ComputerStatus.active,
    query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    ou_dn: Annotated[str | None, Query(max_length=500)] = None,
    operating_system: Annotated[str | None, Query(max_length=120)] = None,
    inactive_days: Annotated[int, Query(ge=1, le=3650)] = 90,
    machine_password_days: Annotated[int, Query(ge=1, le=3650)] = 90,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ComputerListResponse:
    computers = search_computers(
        status_filter,
        query,
        ou_dn,
        operating_system,
        inactive_days,
        machine_password_days,
        limit,
    )
    audit_event(
        "computers_listed",
        operator=principal.subject,
        status=status_filter.value,
        query_present=bool(query),
        ou_filter_present=bool(ou_dn),
        operating_system_filter_present=bool(operating_system),
        inactive_days=inactive_days,
        machine_password_days=machine_password_days,
        result_count=len(computers),
    )
    return ComputerListResponse(
        items=computers,
        count=len(computers),
        limit=limit,
        status=status_filter,
    )


@router.get("/{identifier}", response_model=AdComputer)
def get_computer(
    identifier: str,
    principal: Annotated[Principal, Depends(require_permission(Permission.read_computers))],
) -> AdComputer:
    escaped_identifier = ldap_escape(identifier)
    query_filter = (
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
    settings = get_settings()
    try:
        with ad_connection(settings) as connection:
            connection.search(
                search_base=settings.ad_base_dn,
                search_filter=query_filter,
                attributes=COMPUTER_ATTRIBUTES,
                size_limit=2,
            )
            computer = (
                _entry_to_computer(connection.entries[0].entry_attributes_as_dict)
                if connection.entries
                else None
            )
    except LDAPException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Active Directory computer lookup failed: {exc.__class__.__name__}",
        ) from exc

    audit_event(
        "computer_lookup",
        operator=principal.subject,
        identifier=identifier,
        found=bool(computer),
    )
    if computer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Computer not found.")
    return computer
