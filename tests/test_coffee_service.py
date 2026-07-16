from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from office_food_bot.features.coffee.rendering import coffee_countdown_text
from office_food_bot.features.coffee.service import next_coffee_countdown_update, parse_coffee_time

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


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (1, "1 минуту"),
        (2, "2 минуты"),
        (5, "5 минут"),
        (11, "11 минут"),
        (21, "21 минуту"),
    ],
)
def test_coffee_countdown_uses_russian_minute_forms(
    minutes: int,
    expected: str,
) -> None:
    scheduled_at = NOW + timedelta(minutes=minutes)

    assert coffee_countdown_text(scheduled_at, NOW) == expected


def test_coffee_countdown_says_now_when_meeting_is_due() -> None:
    assert coffee_countdown_text(NOW, NOW) == "сейчас"


def test_next_coffee_countdown_update_is_aligned_with_scheduled_time() -> None:
    now = NOW.replace(second=30)
    scheduled_at = NOW.replace(minute=30)

    assert next_coffee_countdown_update(scheduled_at, now) == NOW.replace(minute=16)


def test_next_coffee_countdown_update_waits_until_last_hour() -> None:
    scheduled_at = NOW + timedelta(hours=4)

    assert next_coffee_countdown_update(scheduled_at, NOW) == (
        scheduled_at - timedelta(minutes=59)
    )


def test_coffee_countdown_has_no_update_during_last_minute() -> None:
    scheduled_at = NOW + timedelta(seconds=60)

    assert next_coffee_countdown_update(scheduled_at, NOW) is None
