from __future__ import annotations

import sqlite3

from office_food_bot.application.users.models import (
    KnownTelegramAccount,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.database import Database
from office_food_bot.features.registration.account_queries import (
    GET_TELEGRAM_ACCOUNT_SQL,
    LIST_SEEN_TELEGRAM_ACCOUNTS_SQL,
    UPSERT_TELEGRAM_ACCOUNT_PROFILE_SQL,
)
from office_food_bot.features.registration.request_queries import (
    DELETE_REGISTRATION_REQUEST_SQL,
    LIST_REQUESTED_REGISTRATION_ACCOUNTS_SQL,
    UPSERT_REGISTRATION_REQUEST_SQL,
)


class TelegramAccountRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def remember(self, profile: TelegramProfile) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_TELEGRAM_ACCOUNT_PROFILE_SQL,
                (
                    profile.telegram_user_id,
                    profile.username,
                    profile.first_name,
                    profile.last_name,
                ),
            )

    def get(self, telegram_user_id: int) -> KnownTelegramAccount | None:
        row = self._database.connection.execute(
            GET_TELEGRAM_ACCOUNT_SQL,
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            return None
        return _known_telegram_account_from_row(row)

    def list_seen(self, limit: int) -> tuple[KnownTelegramAccount, ...]:
        rows = self._database.connection.execute(
            LIST_SEEN_TELEGRAM_ACCOUNTS_SQL,
            (UserStatus.ABANDONED.value, limit),
        ).fetchall()
        return tuple(_known_telegram_account_from_row(row) for row in rows)


class RegistrationRequestRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def request(self, telegram_user_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_REGISTRATION_REQUEST_SQL,
                (telegram_user_id,),
            )

    def clear(self, telegram_user_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(
                DELETE_REGISTRATION_REQUEST_SQL,
                (telegram_user_id,),
            )

    def list_requested(self, limit: int) -> tuple[KnownTelegramAccount, ...]:
        rows = self._database.connection.execute(
            LIST_REQUESTED_REGISTRATION_ACCOUNTS_SQL,
            (UserStatus.ABANDONED.value, limit),
        ).fetchall()
        return tuple(_known_telegram_account_from_row(row) for row in rows)


def _known_telegram_account_from_row(row: sqlite3.Row) -> KnownTelegramAccount:
    return KnownTelegramAccount(
        telegram_user_id=int(row["telegram_user_id"]),
        username=_optional_str(row["username"]),
        first_name=_optional_str(row["first_name"]),
        last_name=_optional_str(row["last_name"]),
    )


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)
