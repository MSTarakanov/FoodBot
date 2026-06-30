from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from office_food_bot.database import Database
from office_food_bot.models import (
    ApprovalKind,
    RegisteredUser,
    RegistrationKind,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.repositories import (
    UserRepository,
    normalize_display_name,
)


@dataclass(frozen=True)
class RegistrationResult:
    kind: RegistrationKind
    user: RegisteredUser


@dataclass(frozen=True)
class ApprovalResult:
    kind: ApprovalKind
    user: RegisteredUser | None


@dataclass(frozen=True)
class BotServices:
    registration: RegistrationService
    presence: PresenceService
    balances: BalanceService


class RegistrationService:
    def __init__(self, users: UserRepository, admin_ids: frozenset[int]) -> None:
        self._users = users
        self.admin_ids = admin_ids

    def register(self, profile: TelegramProfile, raw_display_name: str) -> RegistrationResult:
        display_name = normalize_display_name(raw_display_name)
        if not display_name:
            display_name = profile.first_name
        if len(display_name) > 64:
            display_name = display_name[:64].rstrip()

        existing_user = self._users.get_by_telegram_id(profile.telegram_user_id)
        if existing_user is not None:
            self._users.refresh_telegram_profile(profile)
            return RegistrationResult(_registration_kind_for(existing_user), existing_user)

        user = self._users.create_pending_user(profile, display_name)
        return RegistrationResult(RegistrationKind.CREATED, user)

    def approve(
        self,
        approver_telegram_user_id: int,
        target_telegram_user_id: int,
    ) -> ApprovalResult:
        if not self.can_approve(approver_telegram_user_id):
            return ApprovalResult(ApprovalKind.FORBIDDEN, None)

        user = self._users.approve_by_telegram_id(target_telegram_user_id)
        if user is None:
            return ApprovalResult(ApprovalKind.NOT_FOUND, None)
        return ApprovalResult(ApprovalKind.APPROVED, user)

    def can_approve(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.admin_ids or self._users.is_active_admin(telegram_user_id)


class PresenceService:
    def __init__(
        self,
        users: UserRepository,
        timezone_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._timezone = ZoneInfo(timezone_name)
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def meta(self, telegram_user_id: int, raw_minutes: str) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register Имя"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."

        minutes = _parse_minutes(raw_minutes)
        if minutes is None:
            return "Минуты должны быть положительным числом: /meta 25"

        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        eta = now.astimezone(self._timezone) + timedelta(minutes=minutes)
        return f"{user.display_name} будет в {eta:%H:%M}"


class BalanceService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def balance(self, telegram_user_id: int) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register Имя"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."
        if self._users.count_splitwise_users() == 0:
            return "Splitwise пока не подключен."
        return "Splitwise подключим следующим шагом."


def build_services(
    database: Database,
    admin_ids: frozenset[int],
    timezone_name: str,
    clock: Callable[[], datetime] | None = None,
) -> BotServices:
    users = UserRepository(database)
    return BotServices(
        registration=RegistrationService(users, admin_ids),
        presence=PresenceService(users, timezone_name, clock),
        balances=BalanceService(users),
    )


def _registration_kind_for(user: RegisteredUser) -> RegistrationKind:
    if user.status == UserStatus.ACTIVE:
        return RegistrationKind.ALREADY_ACTIVE
    if user.status == UserStatus.PENDING:
        return RegistrationKind.ALREADY_PENDING
    return RegistrationKind.BLOCKED


def _parse_minutes(raw_minutes: str) -> int | None:
    try:
        minutes = int(raw_minutes.strip())
    except ValueError:
        return None
    if minutes <= 0:
        return None
    if minutes > 24 * 60:
        return None
    return minutes
