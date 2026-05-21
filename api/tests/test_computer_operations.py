import pytest
from fastapi import HTTPException

from app.ad_utils import ACCOUNT_DISABLED_FLAG
from app.computer_operations import (
    ComputerOperationRequest,
    _require_confirmation,
    _set_disabled_flag,
)


def test_set_disabled_flag_enables_computer() -> None:
    assert _set_disabled_flag(ACCOUNT_DISABLED_FLAG, disabled=False) == 0


def test_set_disabled_flag_disables_computer() -> None:
    assert _set_disabled_flag(0, disabled=True) == ACCOUNT_DISABLED_FLAG


def test_computer_operation_requires_confirmation() -> None:
    with pytest.raises(HTTPException):
        _require_confirmation(
            ComputerOperationRequest(
                confirm=False,
                dry_run=True,
                reason="valid reason for test",
            )
        )


def test_computer_operation_accepts_confirmation() -> None:
    _require_confirmation(
        ComputerOperationRequest(
            confirm=True,
            dry_run=True,
            reason="valid reason for test",
        )
    )
