from __future__ import annotations

from typing import Protocol, assert_never

from office_food_bot.application.users.resolver import ActiveUserResolver
from office_food_bot.features.invitations.models import (
    InvitationKind,
    InvitationPreferences,
    InvitationSettingReport,
)


class InvitationPreferenceStore(Protocol):
    def get(self, user_id: int) -> InvitationPreferences: ...

    def save(self, user_id: int, preferences: InvitationPreferences) -> None: ...

    def set_lunch_enabled(self, user_id: int, enabled: bool) -> None: ...

    def set_coffee_enabled(self, user_id: int, enabled: bool) -> None: ...


class InvitationPreferenceService:
    def __init__(
        self,
        active_users: ActiveUserResolver,
        preferences: InvitationPreferenceStore,
    ) -> None:
        self._active_users = active_users
        self._preferences = preferences

    def for_user(self, user_id: int) -> InvitationPreferences:
        return self._preferences.get(user_id)

    def save_initial(self, user_id: int, preferences: InvitationPreferences) -> None:
        self._preferences.save(user_id, preferences)

    def status(
        self,
        telegram_user_id: int,
        kind: InvitationKind,
    ) -> InvitationSettingReport:
        user = self._active_users.require_active(telegram_user_id)
        preferences = self._preferences.get(user.id)
        match kind:
            case InvitationKind.LUNCH:
                enabled = preferences.lunch_enabled
            case InvitationKind.COFFEE:
                enabled = preferences.coffee_enabled
            case _:
                assert_never(kind)
        return InvitationSettingReport(kind, enabled, updated=False)

    def set_enabled(
        self,
        telegram_user_id: int,
        kind: InvitationKind,
        enabled: bool,
    ) -> InvitationSettingReport:
        user = self._active_users.require_active(telegram_user_id)
        match kind:
            case InvitationKind.LUNCH:
                self._preferences.set_lunch_enabled(user.id, enabled)
            case InvitationKind.COFFEE:
                self._preferences.set_coffee_enabled(user.id, enabled)
            case _:
                assert_never(kind)
        return InvitationSettingReport(kind, enabled, updated=True)
