from fastapi import status

from app.ad_errors import ad_modify_error


def test_ad_modify_error_maps_insufficient_access_to_forbidden() -> None:
    error = ad_modify_error(
        "Active Directory modify failed",
        {"description": "insufficientAccessRights", "message": "00000005: SecErr"},
    )

    assert error.status_code == status.HTTP_403_FORBIDDEN
    assert "Permissao negada pelo Active Directory" in error.detail


def test_ad_modify_error_keeps_unexpected_modify_failure_as_bad_gateway() -> None:
    error = ad_modify_error(
        "Active Directory modify failed",
        {"description": "constraintViolation"},
    )

    assert error.status_code == status.HTTP_502_BAD_GATEWAY
    assert error.detail == "Active Directory modify failed: constraintViolation"
