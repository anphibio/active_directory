import pytest
from fastapi import HTTPException

from app.group_operations import (
    GroupMembershipRequest,
    _require_confirmation,
    _require_protected_confirmation,
)
from app.groups import AdGroup


def test_group_operation_requires_confirmation() -> None:
    with pytest.raises(HTTPException):
        _require_confirmation(
            GroupMembershipRequest(
                sam_account_name="user1",
                confirm=False,
                reason="valid reason for test",
            )
        )


def test_group_operation_accepts_confirmation() -> None:
    _require_confirmation(
        GroupMembershipRequest(
            sam_account_name="user1",
            confirm=True,
            reason="valid reason for test",
        )
    )


def test_protected_group_requires_extra_confirmation() -> None:
    group = AdGroup(
        distinguished_name="CN=Domain Admins,CN=Users,DC=example,DC=local",
        common_name="Domain Admins",
        member_count=1,
    )
    request = GroupMembershipRequest(
        sam_account_name="user1",
        confirm=True,
        protected_group_confirm=False,
        reason="valid reason for test",
    )

    with pytest.raises(HTTPException):
        _require_protected_confirmation(request, group)


def test_protected_group_accepts_extra_confirmation() -> None:
    group = AdGroup(
        distinguished_name="CN=Domain Admins,CN=Users,DC=example,DC=local",
        common_name="Domain Admins",
        member_count=1,
    )
    request = GroupMembershipRequest(
        sam_account_name="user1",
        confirm=True,
        protected_group_confirm=True,
        reason="valid reason for test",
    )

    assert _require_protected_confirmation(request, group) is True
