from app.ad_utils import (
    ACCOUNT_DISABLED_FLAG,
    SERVER_TRUST_ACCOUNT_FLAG,
    WORKSTATION_TRUST_ACCOUNT_FLAG,
)
from app.computers import ComputerStatus, _entry_to_computer, build_computer_filter


def test_active_computer_filter_excludes_disabled_accounts() -> None:
    ldap_filter, search_base = build_computer_filter(ComputerStatus.active)

    assert search_base is None
    assert "(objectCategory=computer)" in ldap_filter
    assert f"(!(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG}))" in ldap_filter


def test_disabled_computer_filter_uses_disabled_flag() -> None:
    ldap_filter, _ = build_computer_filter(ComputerStatus.disabled)

    assert f"(userAccountControl:1.2.840.113556.1.4.803:={ACCOUNT_DISABLED_FLAG})" in ldap_filter


def test_server_filter_uses_server_trust_account_flag() -> None:
    ldap_filter, _ = build_computer_filter(ComputerStatus.servers)

    assert f"(userAccountControl:1.2.840.113556.1.4.803:={SERVER_TRUST_ACCOUNT_FLAG})" in ldap_filter


def test_workstation_filter_uses_workstation_trust_account_flag() -> None:
    ldap_filter, _ = build_computer_filter(ComputerStatus.workstations)

    assert f"(userAccountControl:1.2.840.113556.1.4.803:={WORKSTATION_TRUST_ACCOUNT_FLAG})" in ldap_filter


def test_computer_query_filter_is_escaped() -> None:
    ldap_filter, _ = build_computer_filter(ComputerStatus.all, query="srv*")

    assert "srv\\2a" in ldap_filter
    assert "srv*)" not in ldap_filter


def test_ou_dn_sets_search_base() -> None:
    _, search_base = build_computer_filter(ComputerStatus.all, ou_dn="OU=Computers,DC=example,DC=local")

    assert search_base == "OU=Computers,DC=example,DC=local"


def test_entry_to_computer_tolerates_unexpected_numeric_shapes() -> None:
    computer = _entry_to_computer(
        {
            "distinguishedName": ["CN=PC01,DC=example,DC=local"],
            "cn": ["PC01"],
            "userAccountControl": [str(WORKSTATION_TRUST_ACCOUNT_FLAG)],
            "lastLogonTimestamp": [b"0"],
            "pwdLastSet": ["not-a-timestamp"],
        }
    )

    assert computer.common_name == "PC01"
    assert computer.enabled is True
    assert computer.is_workstation is True
    assert computer.password_last_set_at is None


def test_search_computers_uses_paged_search(monkeypatch) -> None:
    from app.computers import search_computers

    calls = {}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_paged_search(connection, **kwargs):
        calls.update(kwargs)
        return []

    monkeypatch.setattr("app.computers.ad_connection", lambda settings: FakeConnection())
    monkeypatch.setattr("app.computers.paged_search", fake_paged_search)

    search_computers(
        ComputerStatus.all,
        query=None,
        ou_dn="OU=Computers,DC=example,DC=local",
        operating_system=None,
        inactive_days=90,
        machine_password_days=90,
        limit=10,
    )

    assert calls["search_base"] == "OU=Computers,DC=example,DC=local"
    assert calls["limit"] == 10
