from __future__ import annotations

import sqlite3
from datetime import date

from office_food_bot.database import Database
from office_food_bot.database.debug_queries import (
    GET_TELEGRAM_DEBUG_ENABLED_SQL,
    UPSERT_TELEGRAM_DEBUG_SQL,
)
from office_food_bot.database.lunch_auto_chat_queries import (
    DISABLE_LUNCH_AUTO_CHAT_SQL,
    GET_LUNCH_AUTO_CHAT_SQL,
    LIST_ENABLED_LUNCH_AUTO_CHATS_SQL,
    UPSERT_LUNCH_AUTO_CHAT_SQL,
)
from office_food_bot.database.lunch_pin_queries import (
    DELETE_LUNCH_PINNED_MESSAGE_SQL,
    GET_LUNCH_PINNED_MESSAGE_SQL,
    UPSERT_LUNCH_PINNED_MESSAGE_SQL,
)
from office_food_bot.database.registration_request_queries import (
    DELETE_REGISTRATION_REQUEST_SQL,
    LIST_REQUESTED_REGISTRATION_ACCOUNTS_SQL,
    UPSERT_REGISTRATION_REQUEST_SQL,
)
from office_food_bot.database.telegram_account_queries import (
    GET_TELEGRAM_ACCOUNT_SQL,
    LIST_SEEN_TELEGRAM_ACCOUNTS_SQL,
    UPSERT_TELEGRAM_ACCOUNT_PROFILE_SQL,
)
from office_food_bot.database.user_queries import (
    COUNT_SPLITWISE_USERS_SQL,
    DELETE_SPLITWISE_USER_BY_USER_ID_SQL,
    GET_REGISTRATION_DETAILS_BY_TELEGRAM_ID_SQL,
    GET_USER_BY_TELEGRAM_ID_SQL,
    INSERT_SPLITWISE_USER_SQL,
    INSERT_USER_SQL,
    LIST_ACTIVE_SPLITWISE_USERS_SQL,
    LIST_ACTIVE_USERS_SQL,
    LIST_PENDING_REGISTRATIONS_SQL,
    LIST_PENDING_USERS_SQL,
    UPDATE_TELEGRAM_PROFILE_SQL,
    UPDATE_USER_REGISTRATION_BY_TELEGRAM_ID_SQL,
    UPDATE_USER_STATUS_BY_TELEGRAM_ID_SQL,
    UPSERT_LINKED_TELEGRAM_ACCOUNT_SQL,
)
from office_food_bot.database.vacation_queries import (
    DELETE_USER_VACATION_SQL,
    GET_USER_VACATION_SQL,
    LIST_ACTIVE_VACATION_USER_IDS_SQL,
    UPSERT_USER_VACATION_SQL,
)
from office_food_bot.models import (
    ActiveSplitwiseUser,
    KnownTelegramAccount,
    LunchAutoChat,
    LunchPinnedMessage,
    PendingRegistration,
    RegisteredUser,
    RegistrationDetails,
    SplitwiseConnection,
    SplitwiseMember,
    TelegramProfile,
    UserRole,
    UserStatus,
    UserVacation,
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

    def list_active_users(self) -> tuple[RegisteredUser, ...]:
        rows = self._database.connection.execute(
            LIST_ACTIVE_USERS_SQL,
            (UserStatus.ACTIVE.value,),
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
                UPSERT_LINKED_TELEGRAM_ACCOUNT_SQL,
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
                UPDATE_USER_STATUS_BY_TELEGRAM_ID_SQL,
                (UserStatus.ACTIVE.value, telegram_user_id),
            )
        return self.get_by_telegram_id(telegram_user_id)

    def abandon_by_telegram_id(self, telegram_user_id: int) -> RegisteredUser | None:
        existing_user = self.get_by_telegram_id(telegram_user_id)
        if existing_user is None:
            return None

        with self._database.connection:
            self._database.connection.execute(
                UPDATE_USER_STATUS_BY_TELEGRAM_ID_SQL,
                (UserStatus.ABANDONED.value, telegram_user_id),
            )
            self._database.connection.execute(
                DELETE_SPLITWISE_USER_BY_USER_ID_SQL,
                (existing_user.id,),
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
            msg = "Enabled lunch auto chat was not found"
            raise RuntimeError(msg)
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
            msg = "Lunch pinned message was not found after upsert"
            raise RuntimeError(msg)
        return pinned_message

    def clear(self, chat_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(
                DELETE_LUNCH_PINNED_MESSAGE_SQL,
                (chat_id,),
            )


class VacationRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, user_id: int) -> UserVacation | None:
        row = self._database.connection.execute(
            GET_USER_VACATION_SQL,
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return _user_vacation_from_row(row)

    def set_until_date(self, user_id: int, until_date: date) -> UserVacation:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_USER_VACATION_SQL,
                (user_id, until_date.isoformat()),
            )

        vacation = self.get(user_id)
        if vacation is None:
            msg = "Saved vacation was not found"
            raise RuntimeError(msg)
        return vacation

    def clear(self, user_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(DELETE_USER_VACATION_SQL, (user_id,))

    def active_user_ids(self, today: date) -> frozenset[int]:
        rows = self._database.connection.execute(
            LIST_ACTIVE_VACATION_USER_IDS_SQL,
            (today.isoformat(),),
        ).fetchall()
        return frozenset(int(row["user_id"]) for row in rows)


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


def _known_telegram_account_from_row(row: sqlite3.Row) -> KnownTelegramAccount:
    return KnownTelegramAccount(
        telegram_user_id=int(row["telegram_user_id"]),
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
        email=_optional_str(row["splitwise_email"]),
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


def _user_vacation_from_row(row: sqlite3.Row) -> UserVacation:
    return UserVacation(
        user_id=int(row["user_id"]),
        until_date=date.fromisoformat(str(row["until_date"])),
    )


def _splitwise_connection_from_row(row: sqlite3.Row) -> SplitwiseConnection | None:
    if row["splitwise_user_id"] is None:
        return None
    return SplitwiseConnection(
        splitwise_user_id=int(row["splitwise_user_id"]),
        email=_optional_str(row["splitwise_email"]),
    )


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)
