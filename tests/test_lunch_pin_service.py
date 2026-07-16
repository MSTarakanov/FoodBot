from __future__ import annotations

from datetime import date

from aiogram import Bot

from office_food_bot.database import Database
from office_food_bot.features.lunch.pins import LunchPinService
from office_food_bot.repositories import LunchPinRepository


class RecordingPinMessenger:
    def __init__(
        self,
        *,
        pin_result: bool = True,
        unpin_result: bool = True,
    ) -> None:
        self._pin_result = pin_result
        self._unpin_result = unpin_result
        self.pins: list[tuple[int, int]] = []
        self.unpins: list[tuple[int, int]] = []

    async def try_pin_chat_message(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
    ) -> bool:
        self.pins.append((chat_id, message_id))
        return self._pin_result

    async def try_unpin_chat_message(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
    ) -> bool:
        self.unpins.append((chat_id, message_id))
        return self._unpin_result


def make_bot() -> Bot:
    return Bot(token="123456:test-token")


async def test_lunch_pin_service_pins_and_stores_new_message(
    database: Database,
) -> None:
    messenger = RecordingPinMessenger()
    pins = LunchPinRepository(database)
    service = LunchPinService(messenger, pins)

    await service.replace_pin(make_bot(), -100, 10, date(2026, 7, 9))

    assert messenger.unpins == []
    assert messenger.pins == [(-100, 10)]
    pinned_message = pins.get(-100)
    assert pinned_message is not None
    assert pinned_message.message_id == 10
    assert pinned_message.lunch_date == date(2026, 7, 9)


async def test_lunch_pin_service_unpins_old_message_before_replacing(
    database: Database,
) -> None:
    messenger = RecordingPinMessenger()
    pins = LunchPinRepository(database)
    pins.upsert(-100, 10, date(2026, 7, 8))
    service = LunchPinService(messenger, pins)

    await service.replace_pin(make_bot(), -100, 11, date(2026, 7, 9))

    assert messenger.unpins == [(-100, 10)]
    assert messenger.pins == [(-100, 11)]
    pinned_message = pins.get(-100)
    assert pinned_message is not None
    assert pinned_message.message_id == 11
    assert pinned_message.lunch_date == date(2026, 7, 9)


async def test_lunch_pin_service_does_not_store_failed_pin(
    database: Database,
) -> None:
    messenger = RecordingPinMessenger(pin_result=False)
    pins = LunchPinRepository(database)
    service = LunchPinService(messenger, pins)

    await service.replace_pin(make_bot(), -100, 10, date(2026, 7, 9))

    assert messenger.pins == [(-100, 10)]
    assert pins.get(-100) is None


async def test_lunch_pin_service_clear_saved_pin_removes_state_even_when_unpin_fails(
    database: Database,
) -> None:
    messenger = RecordingPinMessenger(unpin_result=False)
    pins = LunchPinRepository(database)
    pins.upsert(-100, 10, date(2026, 7, 8))
    service = LunchPinService(messenger, pins)

    await service.clear_saved_pin(make_bot(), -100)

    assert messenger.unpins == [(-100, 10)]
    assert pins.get(-100) is None
