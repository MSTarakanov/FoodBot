from __future__ import annotations

import sqlite3

from office_food_bot.database import Database
from office_food_bot.database.debug_queries import (
    GET_TELEGRAM_DEBUG_ENABLED_SQL,
    UPSERT_TELEGRAM_DEBUG_SQL,
)
from office_food_bot.database.user_queries import (
    APPROVE_USER_BY_TELEGRAM_ID_SQL,
    COUNT_SPLITWISE_USERS_SQL,
    DELETE_SPLITWISE_USER_BY_USER_ID_SQL,
    GET_REGISTRATION_DETAILS_BY_TELEGRAM_ID_SQL,
    GET_USER_BY_TELEGRAM_ID_SQL,
    INSERT_SPLITWISE_USER_SQL,
    INSERT_TELEGRAM_ACCOUNT_SQL,
    INSERT_USER_SQL,
    LIST_ACTIVE_SPLITWISE_USERS_SQL,
    LIST_PENDING_REGISTRATIONS_SQL,
    LIST_PENDING_USERS_SQL,
    UPDATE_TELEGRAM_PROFILE_SQL,
    UPDATE_USER_REGISTRATION_BY_TELEGRAM_ID_SQL,
)
from office_food_bot.models import (
    ActiveSplitwiseUser,
    PendingRegistration,
    RegisteredUser,
    RegistrationDetails,
    SplitwiseConnection,
    SplitwiseMember,
    TelegramProfile,
    UserRole,
    UserStatus,
)


class UserRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get_by_telegram_id(self, telegram_user_id: int) -> RegisteredUser | None:
        row = self._database.connection.execute(
            GET_USER_BY_TELEGRAM_ID_SQL,
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            return None
        return _registered_user_from_row(row)

    def list_pending_users(self) -> tuple[RegisteredUser, ...]:
        rows = self._database.connection.execute(
            LIST_PENDING_USERS_SQL,
            (UserStatus.PENDING.value,),
        ).fetchall()
        return tuple(_registered_user_from_row(row) for row in rows)

    def list_pending_registrations(self) -> tuple[PendingRegistration, ...]:
        rows = self._database.connection.execute(
            LIST_PENDING_REGISTRATIONS_SQL,
            (UserStatus.PENDING.value,),
        ).fetchall()
        return tuple(_pending_registration_from_row(row) for row in rows)

    def list_active_splitwise_users(self) -> tuple[ActiveSplitwiseUser, ...]:
        rows = self._database.connection.execute(
            LIST_ACTIVE_SPLITWISE_USERS_SQL,
            (UserStatus.ACTIVE.value,),
        ).fetchall()
        return tuple(_active_splitwise_user_from_row(row) for row in rows)

    def get_registration_details_by_telegram_id(
        self,
        telegram_user_id: int,
    ) -> RegistrationDetails | None:
        row = self._database.connection.execute(
            GET_REGISTRATION_DETAILS_BY_TELEGRAM_ID_SQL,
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            return None
        return _registration_details_from_row(row)

    def save_pending_registration(
        self,
        profile: TelegramProfile,
        display_name: str,
        splitwise_member: SplitwiseMember | None,
    ) -> RegisteredUser:
        existing_user = self.get_by_telegram_id(profile.telegram_user_id)
        if existing_user is None:
            user = self.create_pending_user(profile, display_name)
        else:
            user = self.update_registration(profile, display_name)

        self._replace_registration_splitwise_user(user.id, splitwise_member)
        refreshed_user = self.get_by_telegram_id(profile.telegram_user_id)
        if refreshed_user is None:
            msg = "Saved registration user was not found"
            raise RuntimeError(msg)
        return refreshed_user

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
                INSERT_USER_SQL,
                (display_name, UserStatus.PENDING.value, UserRole.MEMBER.value),
            )
            user_id = cursor.lastrowid
            if user_id is None:
                msg = "Created user id was not returned"
                raise RuntimeError(msg)
            self._database.connection.execute(
                INSERT_TELEGRAM_ACCOUNT_SQL,
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
                UPDATE_TELEGRAM_PROFILE_SQL,
                (
                    profile.username,
                    profile.first_name,
                    profile.last_name,
                    profile.telegram_user_id,
                ),
            )

    def update_registration(
        self,
        profile: TelegramProfile,
        display_name: str,
    ) -> RegisteredUser:
        with self._database.connection:
            self._database.connection.execute(
                UPDATE_USER_REGISTRATION_BY_TELEGRAM_ID_SQL,
                (display_name, UserStatus.PENDING.value, profile.telegram_user_id),
            )
            self._database.connection.execute(
                UPDATE_TELEGRAM_PROFILE_SQL,
                (
                    profile.username,
                    profile.first_name,
                    profile.last_name,
                    profile.telegram_user_id,
                ),
            )

        user = self.get_by_telegram_id(profile.telegram_user_id)
        if user is None:
            msg = "Updated user was not found"
            raise RuntimeError(msg)
        return user

    def approve_by_telegram_id(self, telegram_user_id: int) -> RegisteredUser | None:
        if self.get_by_telegram_id(telegram_user_id) is None:
            return None

        with self._database.connection:
            self._database.connection.execute(
                APPROVE_USER_BY_TELEGRAM_ID_SQL,
                (UserStatus.ACTIVE.value, telegram_user_id),
            )
        return self.get_by_telegram_id(telegram_user_id)

    def is_active_admin(self, telegram_user_id: int) -> bool:
        user = self.get_by_telegram_id(telegram_user_id)
        return (
            user is not None
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.ADMIN
        )

    def count_splitwise_users(self) -> int:
        count = self._database.connection.execute(COUNT_SPLITWISE_USERS_SQL).fetchone()
        if count is None:
            return 0
        return int(count[0])

    def _replace_registration_splitwise_user(
        self,
        user_id: int,
        splitwise_member: SplitwiseMember | None,
    ) -> None:
        with self._database.connection:
            self._database.connection.execute(
                DELETE_SPLITWISE_USER_BY_USER_ID_SQL,
                (user_id,),
            )
            if splitwise_member is None:
                return
            self._database.connection.execute(
                INSERT_SPLITWISE_USER_SQL,
                (
                    splitwise_member.splitwise_user_id,
                    user_id,
                    splitwise_member.email,
                ),
            )


class DebugRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def is_enabled(self, telegram_user_id: int) -> bool:
        row = self._database.connection.execute(
            GET_TELEGRAM_DEBUG_ENABLED_SQL,
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            return False
        return bool(row["enabled"])

    def set_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_TELEGRAM_DEBUG_SQL,
                (telegram_user_id, int(enabled)),
            )


def normalize_display_name(raw_display_name: str) -> str:
    return " ".join(raw_display_name.split())


def _registered_user_from_row(row: sqlite3.Row) -> RegisteredUser:
    return RegisteredUser(
        id=int(row["id"]),
        telegram_user_id=int(row["telegram_user_id"]),
        display_name=str(row["display_name"]),
        status=UserStatus(str(row["status"])),
        role=UserRole(str(row["role"])),
        username=_optional_str(row["username"]),
        first_name=_optional_str(row["first_name"]),
        last_name=_optional_str(row["last_name"]),
    )


def _pending_registration_from_row(row: sqlite3.Row) -> PendingRegistration:
    return PendingRegistration(
        user=_registered_user_from_row(row),
        splitwise=_splitwise_connection_from_row(row),
    )


def _registration_details_from_row(row: sqlite3.Row) -> RegistrationDetails:
    return RegistrationDetails(
        display_name=str(row["display_name"]),
        splitwise=_splitwise_connection_from_row(row),
    )


def _active_splitwise_user_from_row(row: sqlite3.Row) -> ActiveSplitwiseUser:
    return ActiveSplitwiseUser(
        display_name=str(row["display_name"]),
        splitwise_user_id=int(row["splitwise_user_id"]),
        email=str(row["splitwise_email"]),
    )


def _splitwise_connection_from_row(row: sqlite3.Row) -> SplitwiseConnection | None:
    if row["splitwise_user_id"] is None:
        return None
    return SplitwiseConnection(
        splitwise_user_id=int(row["splitwise_user_id"]),
        email=str(row["splitwise_email"]),
    )


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)
