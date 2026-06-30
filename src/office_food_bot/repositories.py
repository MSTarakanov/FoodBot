from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal, cast

from office_food_bot.database import Database

UserStatus = Literal["pending", "active", "rejected", "disabled"]
UserRole = Literal["member", "admin"]


@dataclass(frozen=True)
class TelegramProfile:
    telegram_user_id: int
    username: str | None
    first_name: str
    last_name: str | None


@dataclass(frozen=True)
class RegisteredUser:
    id: int
    telegram_user_id: int
    display_name: str
    status: UserStatus
    role: UserRole
    username: str | None
    first_name: str | None
    last_name: str | None


class UserRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_by_telegram_id(self, telegram_user_id: int) -> RegisteredUser | None:
        row = self._database.connection.execute(
            """
            SELECT
                users.id,
                users.display_name,
                users.status,
                users.role,
                telegram_accounts.telegram_user_id,
                telegram_accounts.username,
                telegram_accounts.first_name,
                telegram_accounts.last_name
            FROM telegram_accounts
            JOIN users ON users.id = telegram_accounts.user_id
            WHERE telegram_accounts.telegram_user_id = ?
            """,
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            return None
        return _registered_user_from_row(row)

    def create_pending_user(
        self,
        profile: TelegramProfile,
        display_name: str,
    ) -> RegisteredUser:
        existing_user = self.get_by_telegram_id(profile.telegram_user_id)
        if existing_user is not None:
            return existing_user

        with self._database.connection:
            cursor = self._database.connection.execute(
                """
                INSERT INTO users (display_name, status, role)
                VALUES (?, 'pending', 'member')
                """,
                (display_name,),
            )
            user_id = cursor.lastrowid
            if user_id is None:
                msg = "Created user id was not returned"
                raise RuntimeError(msg)
            self._database.connection.execute(
                """
                INSERT INTO telegram_accounts (
                    telegram_user_id,
                    user_id,
                    username,
                    first_name,
                    last_name
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    profile.telegram_user_id,
                    user_id,
                    profile.username,
                    profile.first_name,
                    profile.last_name,
                ),
            )

        user = self.get_by_telegram_id(profile.telegram_user_id)
        if user is None:
            msg = "Created user was not found"
            raise RuntimeError(msg)
        return user

    def refresh_telegram_profile(self, profile: TelegramProfile) -> None:
        with self._database.connection:
            self._database.connection.execute(
                """
                UPDATE telegram_accounts
                SET username = ?,
                    first_name = ?,
                    last_name = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_user_id = ?
                """,
                (
                    profile.username,
                    profile.first_name,
                    profile.last_name,
                    profile.telegram_user_id,
                ),
            )

    def approve_by_telegram_id(self, telegram_user_id: int) -> RegisteredUser | None:
        if self.get_by_telegram_id(telegram_user_id) is None:
            return None

        with self._database.connection:
            self._database.connection.execute(
                """
                UPDATE users
                SET status = 'active',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT user_id
                    FROM telegram_accounts
                    WHERE telegram_user_id = ?
                )
                """,
                (telegram_user_id,),
            )
        return self.get_by_telegram_id(telegram_user_id)

    def is_active_admin(self, telegram_user_id: int) -> bool:
        user = self.get_by_telegram_id(telegram_user_id)
        return user is not None and user.status == "active" and user.role == "admin"

    def count_splitwise_users(self) -> int:
        count = self._database.connection.execute(
            "SELECT COUNT(*) FROM splitwise_users"
        ).fetchone()
        if count is None:
            return 0
        return int(count[0])


def normalize_display_name(raw_display_name: str) -> str:
    return " ".join(raw_display_name.split())


def _registered_user_from_row(row: sqlite3.Row) -> RegisteredUser:
    return RegisteredUser(
        id=int(row["id"]),
        telegram_user_id=int(row["telegram_user_id"]),
        display_name=str(row["display_name"]),
        status=cast(UserStatus, str(row["status"])),
        role=cast(UserRole, str(row["role"])),
        username=_optional_str(row["username"]),
        first_name=_optional_str(row["first_name"]),
        last_name=_optional_str(row["last_name"]),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
