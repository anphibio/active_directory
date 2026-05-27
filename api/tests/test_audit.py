from starlette.requests import Request

from app.audit import client_origin_from_request
from app.config import get_settings


def _request(client_host: str, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/audit/events",
            "headers": headers or [],
            "client": (client_host, 45123),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def test_client_origin_ignores_forwarded_headers_from_untrusted_client(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.19.0.0/16")
    get_settings.cache_clear()

    request = _request(
        "203.0.113.10",
        [(b"x-forwarded-for", b"198.51.100.20")],
    )

    assert client_origin_from_request(request) == "203.0.113.10"


def test_client_origin_uses_first_forwarded_ip_from_trusted_proxy(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.19.0.0/16")
    get_settings.cache_clear()

    request = _request(
        "172.19.0.6",
        [(b"x-forwarded-for", b"198.51.100.20, 172.19.0.6")],
    )

    assert client_origin_from_request(request) == "198.51.100.20"


def test_client_origin_uses_x_real_ip_from_trusted_proxy_when_forwarded_for_is_absent(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "172.19.0.0/16")
    get_settings.cache_clear()

    request = _request("172.19.0.6", [(b"x-real-ip", b"198.51.100.21")])

    assert client_origin_from_request(request) == "198.51.100.21"
