from datetime import UTC, datetime

from app.ad_utils import ACCOUNT_DISABLED_FLAG, NEVER_EXPIRES_FLAG, ldap_escape
from app.users import UserStatus, _entry_to_user, build_user_filter, search_users


def test_ldap_escape_handles_special_characters() -> None:
    assert ldap_escape(r"a*b(c)d\e") == r"a\2ab\28c\29d\5ce"


def test_active_user_filter_excludes_disabled_accounts() -> None:
    ldap_filter = build_user_filter(UserStatus.active)

    assert "(objectCategory=person)" in ldap_filter
    assert "(objectClass=user)" in ldap_filter
    assert f"(!(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG}))" in ldap_filter


def test_disabled_user_filter_uses_account_disabled_flag() -> None:
    ldap_filter = build_user_filter(UserStatus.disabled)

    assert f"(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG})" in ldap_filter


def test_password_never_expires_filter_uses_expected_flag() -> None:
    ldap_filter = build_user_filter(UserStatus.password_never_expires)

    assert f"(userAccountControl:1.2.840.113556.1.4.803:={NEVER_EXPIRES_FLAG})" in ldap_filter


def test_query_filter_is_escaped() -> None:
    ldap_filter = build_user_filter(UserStatus.all, query="admin*")

    assert "admin\\2a" in ldap_filter
    assert "admin*)" not in ldap_filter


def test_locked_user_filter_uses_lockout_fields() -> None:
    ldap_filter = build_user_filter(UserStatus.locked)

    assert "(lockoutTime>=1)" in ldap_filter
    assert "(userAccountControl:1.2.840.113556.1.4.803:=16)" in ldap_filter


def test_entry_to_user_tolerates_unexpected_numeric_shapes() -> None:
    user = _entry_to_user(
        {
            "distinguishedName": ["CN=Usuario Teste,DC=example,DC=local"],
            "sAMAccountName": ["usuario.teste"],
            "userAccountControl": ["512"],
            "lockoutTime": [datetime(2026, 5, 19, tzinfo=UTC)],
            "whenCreated": [datetime(2026, 5, 19, tzinfo=UTC)],
            "whenChanged": ["invalid-date"],
            "lastLogonTimestamp": ["0"],
            "pwdLastSet": [b"0"],
        }
    )

    assert user.sam_account_name == "usuario.teste"
    assert user.enabled is True
    assert user.locked is True
    assert user.created_at is not None
    assert user.changed_at is None


def test_search_users_uses_ou_dn_as_search_base(monkeypatch) -> None:
    calls = {}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_paged_search(connection, **kwargs):
        calls.update(kwargs)
        return []

    monkeypatch.setattr("app.users.ad_connection", lambda settings: FakeConnection())
    monkeypatch.setattr("app.users.paged_search", fake_paged_search)

    search_users(UserStatus.all, query=None, group_dn=None, inactive_days=90, limit=10, ou_dn="OU=Users,DC=example,DC=local")

    assert calls["search_base"] == "OU=Users,DC=example,DC=local"
