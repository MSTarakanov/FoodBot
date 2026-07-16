from __future__ import annotations

from office_food_bot.invitation_models import InvitationKind, InvitationSettingReport
from office_food_bot.invitation_repositories import InvitationPreferenceRepository
from office_food_bot.models import InvitationPreferences
from office_food_bot.services.user_access import ActiveUserResolver


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
        enabled = (
            preferences.lunch_enabled
            if kind == InvitationKind.LUNCH
            else preferences.coffee_enabled
        )
        return InvitationSettingReport(kind, enabled, updated=False)

    def set_enabled(
        self,
        telegram_user_id: int,
        kind: InvitationKind,
        enabled: bool,
    ) -> InvitationSettingReport:
        user = self._active_users.require_validated(telegram_user_id)
        if kind == InvitationKind.LUNCH:
            self._preferences.set_lunch_enabled(user.id, enabled)
        else:
            self._preferences.set_coffee_enabled(user.id, enabled)
        return InvitationSettingReport(kind, enabled, updated=True)
