from fastapi import HTTPException, status

from app.config import get_settings


def require_safe_write_transport() -> None:
    settings = get_settings()
    if settings.require_ldaps_for_writes and not settings.ad_use_ldaps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Write operations require LDAPS. Set AD_USE_LDAPS=true or use dry-run only.",
        )


def validate_production_startup() -> bool:
    settings = get_settings()
    errors = settings.production_errors()
    if errors:
        print(
            '{"event":"production_hardening_failed","errors":"'
            + "; ".join(errors)
            + '"}',
            flush=True,
        )
        return False
    return True
