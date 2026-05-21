import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from ldap3 import ALL, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException

from app.config import Settings


@dataclass(frozen=True)
class AdConnectionResult:
    status: str
    server: str
    use_ldaps: bool
    bind_successful: bool
    message: str


def _tls_config(settings: Settings) -> Tls | None:
    if not settings.ad_use_ldaps:
        return None

    validate = ssl.CERT_REQUIRED if settings.ad_tls_require_cert else ssl.CERT_NONE
    return Tls(
        ca_certs_file=settings.ad_ca_cert_path if settings.ad_tls_require_cert else None,
        validate=validate,
        version=ssl.PROTOCOL_TLS_CLIENT,
    )


def build_server(settings: Settings) -> Server:
    return Server(
        settings.ad_server,
        get_info=ALL,
        connect_timeout=settings.ad_search_timeout_seconds,
        use_ssl=settings.ad_use_ldaps,
        tls=_tls_config(settings),
    )


@contextmanager
def ad_connection(settings: Settings) -> Iterator[Connection]:
    server = build_server(settings)
    connection = Connection(
        server,
        user=settings.ad_bind_dn,
        password=settings.ad_bind_password.get_secret_value(),
        auto_bind=True,
        receive_timeout=settings.ad_search_timeout_seconds,
    )
    try:
        yield connection
    finally:
        connection.unbind()


def test_ad_connection(settings: Settings) -> AdConnectionResult:
    missing_variables = settings.missing_ad_variables()
    if missing_variables:
        return AdConnectionResult(
            status="not_configured",
            server=settings.ad_server,
            use_ldaps=settings.ad_use_ldaps,
            bind_successful=False,
            message=f"Missing required variables: {', '.join(missing_variables)}",
        )

    try:
        with ad_connection(settings):
            return AdConnectionResult(
                status="ok",
                server=settings.ad_server,
                use_ldaps=settings.ad_use_ldaps,
                bind_successful=True,
                message="Connection and bind succeeded.",
            )
    except LDAPException as exc:
        return AdConnectionResult(
            status="error",
            server=settings.ad_server,
            use_ldaps=settings.ad_use_ldaps,
            bind_successful=False,
            message=exc.__class__.__name__,
        )
    except OSError as exc:
        return AdConnectionResult(
            status="error",
            server=settings.ad_server,
            use_ldaps=settings.ad_use_ldaps,
            bind_successful=False,
            message=exc.__class__.__name__,
        )


def paged_search(
    connection: Connection,
    search_base: str,
    search_filter: str,
    attributes: list[str],
    limit: int,
    page_size: int = 500,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    cookie: bytes | str | None = None
    effective_page_size = max(1, min(page_size, limit))

    while len(collected) < limit:
        remaining = limit - len(collected)
        connection.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=attributes,
            paged_size=min(effective_page_size, remaining),
            paged_cookie=cookie,
        )
        collected.extend(entry.entry_attributes_as_dict for entry in connection.entries[:remaining])

        controls = connection.result.get("controls") if isinstance(connection.result, dict) else None
        paging = controls.get("1.2.840.113556.1.4.319") if isinstance(controls, dict) else None
        value = paging.get("value") if isinstance(paging, dict) else None
        cookie = value.get("cookie") if isinstance(value, dict) else None
        if not cookie:
            break

    return collected[:limit]
