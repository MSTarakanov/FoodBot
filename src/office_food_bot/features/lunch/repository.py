from __future__ import annotations

import sqlite3
from datetime import date

from office_food_bot.database import Database
from office_food_bot.features.lunch.auto_queries import (
    DISABLE_LUNCH_AUTO_CHAT_SQL,
    GET_LUNCH_AUTO_CHAT_SQL,
    LIST_ENABLED_LUNCH_AUTO_CHATS_SQL,
    UPSERT_LUNCH_AUTO_CHAT_SQL,
)
from office_food_bot.features.lunch.models import LunchAutoChat, LunchPinnedMessage
from office_food_bot.features.lunch.pin_queries import (
    DELETE_LUNCH_PINNED_MESSAGE_SQL,
    GET_LUNCH_PINNED_MESSAGE_SQL,
    UPSERT_LUNCH_PINNED_MESSAGE_SQL,
)


class LunchAutoChatRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def enable(self, chat_id: int, title: str | None) -> LunchAutoChat:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_LUNCH_AUTO_CHAT_SQL,
                (chat_id, title),
            )

        chat = self.get(chat_id)
        if chat is None:
            raise RuntimeError("Enabled lunch auto chat was not found")
        return chat

    def disable(self, chat_id: int) -> LunchAutoChat | None:
        existing_chat = self.get(chat_id)
        if existing_chat is None:
            return None

        with self._database.connection:
            self._database.connection.execute(DISABLE_LUNCH_AUTO_CHAT_SQL, (chat_id,))

        return self.get(chat_id)

    def get(self, chat_id: int) -> LunchAutoChat | None:
        row = self._database.connection.execute(
            GET_LUNCH_AUTO_CHAT_SQL,
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return _lunch_auto_chat_from_row(row)

    def list_enabled(self) -> tuple[LunchAutoChat, ...]:
        rows = self._database.connection.execute(
            LIST_ENABLED_LUNCH_AUTO_CHATS_SQL,
        ).fetchall()
        return tuple(_lunch_auto_chat_from_row(row) for row in rows)


class LunchPinRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, chat_id: int) -> LunchPinnedMessage | None:
        row = self._database.connection.execute(
            GET_LUNCH_PINNED_MESSAGE_SQL,
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return _lunch_pinned_message_from_row(row)

    def upsert(
        self,
        chat_id: int,
        message_id: int,
        lunch_date: date,
    ) -> LunchPinnedMessage:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_LUNCH_PINNED_MESSAGE_SQL,
                (chat_id, message_id, lunch_date.isoformat()),
            )

        pinned_message = self.get(chat_id)
        if pinned_message is None:
            raise RuntimeError("Lunch pinned message was not found after upsert")
        return pinned_message

    def clear(self, chat_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(
                DELETE_LUNCH_PINNED_MESSAGE_SQL,
                (chat_id,),
            )


def _lunch_auto_chat_from_row(row: sqlite3.Row) -> LunchAutoChat:
    return LunchAutoChat(
        chat_id=int(row["chat_id"]),
        title=_optional_str(row["title"]),
        enabled=bool(row["enabled"]),
    )


def _lunch_pinned_message_from_row(row: sqlite3.Row) -> LunchPinnedMessage:
    return LunchPinnedMessage(
        chat_id=int(row["chat_id"]),
        message_id=int(row["message_id"]),
        lunch_date=date.fromisoformat(str(row["lunch_date"])),
    )


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)
