from dataclasses import dataclass

from fastapi import HTTPException, status
from ldap3 import Connection
from ldap3.core.exceptions import LDAPException

from app.ad_client import ad_connection, build_server, paged_search
from app.ad_utils import ldap_escape
from app.audit import audit_event
from app.config import get_settings
from app.security import Role


LOGIN_ATTRIBUTES = [
    "distinguishedName",
    "sAMAccountName",
    "userPrincipalName",
    "displayName",
    "mail",
    "memberOf",
]


@dataclass(frozen=True)
class AuthenticatedAdUser:
    subject: str
    display_name: str | None
    email: str | None
    distinguished_name: str
    member_dns: list[str]
    roles: list[Role]


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


def _text(entry: dict[str, object], name: str) -> str | None:
    value = _first(entry, name)
    return str(value) if value not in (None, "") else None


def _normalize_dn(value: str | None) -> str:
    return (value or "").strip().lower()


def login_identity(username: str) -> str:
    username = username.strip()
    settings = get_settings()
    if "\\" in username or "@" in username or not settings.ad_login_domain:
        return username
    return f"{username}@{settings.ad_login_domain}"


def sam_from_login(username: str) -> str:
    username = username.strip()
    if "\\" in username:
        username = username.rsplit("\\", 1)[-1]
    if "@" in username:
        username = username.split("@", 1)[0]
    return username


def roles_from_group_dns(member_dns: list[str]) -> list[Role]:
    settings = get_settings()
    user_groups = {_normalize_dn(group_dn) for group_dn in member_dns if group_dn}
    roles: list[Role] = []
    for role_name, group_dn in settings.ad_role_group_dns().items():
        if _normalize_dn(group_dn) in user_groups:
            roles.append(Role(role_name))
    return roles


def _find_user_entry(username: str) -> dict[str, object] | None:
    settings = get_settings()
    sam_account_name = sam_from_login(username)
    escaped_username = ldap_escape(username)
    escaped_sam = ldap_escape(sam_account_name)
    search_filter = (
        "(&"
        "(objectCategory=person)"
        "(objectClass=user)"
        "(|"
        f"(sAMAccountName={escaped_sam})"
        f"(userPrincipalName={escaped_username})"
        ")"
        ")"
    )

    with ad_connection(settings) as connection:
        entries = paged_search(
            connection,
            search_base=settings.ad_base_dn,
            search_filter=search_filter,
            attributes=LOGIN_ATTRIBUTES,
            limit=1,
        )
        return entries[0] if entries else None


def _resolve_group_dns(user_dn: str, direct_member_dns: list[str]) -> list[str]:
    settings = get_settings()
    group_dns = {str(group_dn) for group_dn in direct_member_dns if group_dn}
    if not user_dn:
        return sorted(group_dns)

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
            limit=1000,
        )
    for entry in entries:
        group_dn = _text(entry, "distinguishedName")
        if group_dn:
            group_dns.add(group_dn)
    return sorted(group_dns)


def _validate_user_credentials(username: str, password: str) -> None:
    settings = get_settings()
    if not password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas.")

    server = build_server(settings)
    connection = Connection(
        server,
        user=login_identity(username),
        password=password,
        auto_bind=True,
        receive_timeout=settings.ad_search_timeout_seconds,
    )
    connection.unbind()


def authenticate_ad_user(username: str, password: str) -> AuthenticatedAdUser:
    try:
        _validate_user_credentials(username, password)
        entry = _find_user_entry(username)
    except LDAPException as exc:
        audit_event("ad_login_failed", username=sam_from_login(username), reason=exc.__class__.__name__)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas.") from exc
    except OSError as exc:
        audit_event("ad_login_failed", username=sam_from_login(username), reason=exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nao foi possivel consultar o Active Directory: {exc.__class__.__name__}",
        ) from exc

    if entry is None:
        audit_event("ad_login_failed", username=sam_from_login(username), reason="user_not_found")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario nao localizado no AD.")

    direct_member_dns = [str(group_dn) for group_dn in _list(entry, "memberOf")]
    user_dn = _text(entry, "distinguishedName") or ""
    member_dns = _resolve_group_dns(user_dn, direct_member_dns)
    roles = roles_from_group_dns(member_dns)
    if not roles:
        audit_event(
            "ad_login_denied",
            username=sam_from_login(username),
            distinguished_name=_text(entry, "distinguishedName"),
            group_count=len(member_dns),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario autenticado, mas sem grupo autorizado para acessar a aplicacao.",
        )

    subject = _text(entry, "sAMAccountName") or sam_from_login(username)
    return AuthenticatedAdUser(
        subject=subject,
        display_name=_text(entry, "displayName"),
        email=_text(entry, "mail"),
        distinguished_name=user_dn,
        member_dns=member_dns,
        roles=roles,
    )
