from __future__ import annotations

from typing import assert_never

from office_food_bot.features.invitations.models import InvitationKind, InvitationSettingReport
from office_food_bot.features.invitations.repository import InvitationPreferenceRepository
from office_food_bot.features.users.access import ActiveUserResolver
from office_food_bot.models import InvitationPreferences


class InvitationPreferenceService:
    def __init__(
        self,
        active_users: ActiveUserResolver,
        preferences: InvitationPreferenceRepository,
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
        user = self._active_users.require_validated(telegram_user_id)
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
        user = self._active_users.require_validated(telegram_user_id)
        match kind:
            case InvitationKind.LUNCH:
                self._preferences.set_lunch_enabled(user.id, enabled)
            case InvitationKind.COFFEE:
                self._preferences.set_coffee_enabled(user.id, enabled)
            case _:
                assert_never(kind)
        return InvitationSettingReport(kind, enabled, updated=True)
