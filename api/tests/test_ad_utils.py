from datetime import UTC, datetime

from app.ad_utils import ad_int, ad_timestamp_to_datetime, datetime_to_ad_timestamp


def test_ad_int_accepts_common_ad_numeric_shapes() -> None:
    assert ad_int("512") == 512
    assert ad_int([1]) == 0
    assert ad_int(b"16") == 16
    assert ad_int("not-a-number") == 0
    assert ad_int(None, default=7) == 7


def test_ad_int_converts_datetime_to_ad_timestamp() -> None:
    value = datetime(2026, 5, 19, tzinfo=UTC)

    assert ad_int(value) == datetime_to_ad_timestamp(value)


def test_ad_timestamp_to_datetime_handles_invalid_values() -> None:
    assert ad_timestamp_to_datetime(None) is None
    assert ad_timestamp_to_datetime("0") is None
    assert ad_timestamp_to_datetime("not-a-timestamp") is None
