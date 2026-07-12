from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.invitation_repositories import InvitationPreferenceRepository
from office_food_bot.models import InvitationPreferences, RegisteredUser, UserStatus
from office_food_bot.repositories import UserRepository


@dataclass(frozen=True, slots=True)
class InvitationUserAccess:
    user: RegisteredUser | None
    denial_text: str | None


class InvitationPreferenceService:
    def __init__(
        self,
        users: UserRepository,
        preferences: InvitationPreferenceRepository,
    ) -> None:
        self._users = users
        self._preferences = preferences

    def for_user(self, user_id: int) -> InvitationPreferences:
        return self._preferences.get(user_id)

    def save_initial(self, user_id: int, preferences: InvitationPreferences) -> None:
        self._preferences.save(user_id, preferences)

    def lunch_status_text(self, telegram_user_id: int) -> str:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return access.denial_text or "Регистрация сейчас неактивна."
        enabled = self._preferences.get(access.user.id).lunch_enabled
        state = "включены" if enabled else "выключены"
        return (
            f"Приглашения на ланч: {state}.\n\n"
            "Изменить настройку: /lunch on или /lunch off."
        )

    def set_lunch(self, telegram_user_id: int, enabled: bool) -> str:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return access.denial_text or "Регистрация сейчас неактивна."
        self._preferences.set_lunch_enabled(access.user.id, enabled)
        state = "включены" if enabled else "выключены"
        return f"Приглашения на ланч {state}."

    def set_coffee(self, telegram_user_id: int, enabled: bool) -> str:
        access = self._active_user(telegram_user_id)
        if access.user is None:
            return access.denial_text or "Регистрация сейчас неактивна."
        self._preferences.set_coffee_enabled(access.user.id, enabled)
        state = "включены" if enabled else "выключены"
        return f"Приглашения на кофе {state}."

    def _active_user(self, telegram_user_id: int) -> InvitationUserAccess:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return InvitationUserAccess(None, _registration_required_text())
        if user.status == UserStatus.PENDING:
            return InvitationUserAccess(None, "Регистрация еще ждет аппрува.")
        if user.status != UserStatus.ACTIVE:
            return InvitationUserAccess(None, "Регистрация сейчас неактивна.")
        return InvitationUserAccess(user, None)


def registration_required_text() -> str:
    return _registration_required_text()


def _registration_required_text() -> str:
    return (
        "Чтобы пользоваться этой функцией, сначала зарегистрируйся.\n"
        "В личном чате с ботом запусти /register и пройди регистрацию сам "
        "или отправь /request_register, чтобы тебя зарегистрировал администратор."
    )
