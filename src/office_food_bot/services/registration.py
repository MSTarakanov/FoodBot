from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.models import (
    ApprovalKind,
    RegisteredUser,
    RegistrationKind,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.repositories import UserRepository, normalize_display_name


@dataclass(frozen=True)
class RegistrationResult:
    kind: RegistrationKind
    user: RegisteredUser


@dataclass(frozen=True)
class ApprovalResult:
    kind: ApprovalKind
    user: RegisteredUser | None


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


def _registration_kind_for(user: RegisteredUser) -> RegistrationKind:
    if user.status == UserStatus.ACTIVE:
        return RegistrationKind.ALREADY_ACTIVE
    if user.status == UserStatus.PENDING:
        return RegistrationKind.ALREADY_PENDING
    return RegistrationKind.BLOCKED
