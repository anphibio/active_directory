from app.ad_auth import _resolve_group_dns, login_identity, roles_from_group_dns, sam_from_login
from app.config import get_settings
from app.security import Role


def test_login_identity_appends_configured_domain(monkeypatch) -> None:
    monkeypatch.setenv("AD_LOGIN_DOMAIN", "tce.hml")
    get_settings.cache_clear()

    assert login_identity("anderson.bandeira") == "anderson.bandeira@tce.hml"
    assert login_identity(r"TCE\anderson.bandeira") == r"TCE\anderson.bandeira"
    assert login_identity("anderson.bandeira@tce.hml") == "anderson.bandeira@tce.hml"


def test_sam_from_login_normalizes_common_login_formats() -> None:
    assert sam_from_login("anderson.bandeira@tce.hml") == "anderson.bandeira"
    assert sam_from_login(r"TCE\anderson.bandeira") == "anderson.bandeira"
    assert sam_from_login("anderson.bandeira") == "anderson.bandeira"


def test_roles_from_group_dns_uses_configured_dns(monkeypatch) -> None:
    monkeypatch.setenv("AD_ROLE_ADMIN_GROUP_DN", "CN=ADM,OU=Grupos,DC=tce,DC=hml")
    monkeypatch.setenv("AD_ROLE_VIEWER_GROUP_DN", "CN=Leitores,OU=Grupos,DC=tce,DC=hml")
    get_settings.cache_clear()

    roles = roles_from_group_dns(
        [
            "CN=ADM,OU=Grupos,DC=tce,DC=hml",
            "CN=Outro,OU=Grupos,DC=tce,DC=hml",
        ]
    )

    assert roles == [Role.admin]


def test_resolve_group_dns_includes_nested_groups(monkeypatch) -> None:
    import app.ad_auth as ad_auth

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_paged_search(connection, **kwargs):
        return [{"distinguishedName": ["CN=Nested,OU=Grupos,DC=tce,DC=hml"]}]

    monkeypatch.setattr(ad_auth, "ad_connection", lambda settings: FakeConnection(), raising=False)
    monkeypatch.setattr(ad_auth, "paged_search", fake_paged_search)

    groups = _resolve_group_dns(
        "CN=Usuario,OU=Usuarios,DC=tce,DC=hml",
        ["CN=Direto,OU=Grupos,DC=tce,DC=hml"],
    )

    assert "CN=Direto,OU=Grupos,DC=tce,DC=hml" in groups
    assert "CN=Nested,OU=Grupos,DC=tce,DC=hml" in groups
