from app.groups import GroupStatus, _entry_to_group, build_group_filter, search_groups


def test_group_filter_defaults_to_group_object_class() -> None:
    ldap_filter = build_group_filter()

    assert "(objectClass=group)" in ldap_filter


def test_empty_group_filter_requires_no_member_attribute() -> None:
    ldap_filter = build_group_filter(GroupStatus.empty)

    assert "(!(member=*))" in ldap_filter


def test_group_filter_without_description() -> None:
    ldap_filter = build_group_filter(GroupStatus.without_description)

    assert "(!(description=*))" in ldap_filter


def test_group_query_filter_is_escaped() -> None:
    ldap_filter = build_group_filter(GroupStatus.all, query="admin*")

    assert "admin\\2a" in ldap_filter
    assert "admin*)" not in ldap_filter


def test_entry_to_group_tolerates_invalid_group_type() -> None:
    group = _entry_to_group(
        {
            "distinguishedName": ["CN=Grupo,DC=example,DC=local"],
            "cn": ["Grupo"],
            "member": ["CN=User,DC=example,DC=local"],
            "groupType": ["not-a-number"],
        }
    )

    assert group.common_name == "Grupo"
    assert group.member_count == 1
    assert group.group_type == 0


def test_entry_to_group_counts_ranged_members() -> None:
    group = _entry_to_group(
        {
            "distinguishedName": ["CN=Grupo,DC=example,DC=local"],
            "cn": ["Grupo"],
            "member;range=0-1499": ["CN=User1,DC=example,DC=local", "CN=User2,DC=example,DC=local"],
            "member;range=1500-*": ["CN=User3,DC=example,DC=local"],
        }
    )

    assert group.member_count == 3


def test_search_groups_uses_ou_dn_as_search_base(monkeypatch) -> None:
    calls = {}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    def fake_paged_search(connection, **kwargs):
        calls.update(kwargs)
        return []

    monkeypatch.setattr("app.groups.ad_connection", lambda settings: FakeConnection())
    monkeypatch.setattr("app.groups.paged_search", fake_paged_search)

    search_groups(GroupStatus.all, query=None, limit=10, ou_dn="OU=Groups,DC=example,DC=local")

    assert calls["search_base"] == "OU=Groups,DC=example,DC=local"
