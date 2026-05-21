from datetime import UTC, datetime, timedelta


AD_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)
NEVER_EXPIRES_FLAG = 0x10000
ACCOUNT_DISABLED_FLAG = 0x0002
NORMAL_ACCOUNT_FLAG = 0x0200
LOCKOUT_FLAG = 0x0010
WORKSTATION_TRUST_ACCOUNT_FLAG = 0x1000
SERVER_TRUST_ACCOUNT_FLAG = 0x2000
TRUSTED_FOR_DELEGATION_FLAG = 0x80000


def ldap_escape(value: str) -> str:
    replacements = {
        "\\": r"\5c",
        "*": r"\2a",
        "(": r"\28",
        ")": r"\29",
        "\x00": r"\00",
    }
    return "".join(replacements.get(char, char) for char in value)


def ad_timestamp_to_datetime(value: object) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    try:
        return AD_EPOCH + timedelta(microseconds=timestamp / 10)
    except OverflowError:
        return None


def datetime_to_ad_timestamp(value: datetime) -> int:
    normalized = value.astimezone(UTC)
    delta = normalized - AD_EPOCH
    return int(delta.total_seconds() * 10_000_000)


def ad_int(value: object, default: int = 0) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, datetime):
        return datetime_to_ad_timestamp(value)
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def is_flag_set(user_account_control: int | None, flag: int) -> bool:
    return bool((user_account_control or 0) & flag)
