from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from office_food_bot.services.coffee import parse_coffee_time

BELGRADE = ZoneInfo("Europe/Belgrade")
NOW = datetime(2026, 7, 7, 12, 15, tzinfo=BELGRADE)


@pytest.mark.parametrize(
    ("raw_value", "expected_local_time"),
    [
        ("15", "12:30"),
        ("16:30", "16:30"),
    ],
)
def test_parse_coffee_time_supports_minutes_and_local_time(
    raw_value: str,
    expected_local_time: str,
) -> None:
    parsed = parse_coffee_time(raw_value, NOW, BELGRADE)

    assert parsed is not None
    assert parsed.tzinfo == UTC
    assert parsed.astimezone(BELGRADE).strftime("%H:%M") == expected_local_time


@pytest.mark.parametrize(
    "raw_value",
    ["", "coffee", "-5", "0", "16:30:01"],
)
def test_parse_coffee_time_rejects_invalid_values(raw_value: str) -> None:
    assert parse_coffee_time(raw_value, NOW, BELGRADE) is None
