from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.application.splitwise.models import SplitwiseMember
from office_food_bot.application.users.models import TelegramProfile
from office_food_bot.features.registration.models import RegistrationDetails
from office_food_bot.flows.contracts import FlowDraft


@dataclass(frozen=True, slots=True)
class RegistrationDraft(FlowDraft):
    target: TelegramProfile
    requested_display_name: str | None = None
    splitwise_member: SplitwiseMember | None = None
    lunch_invitations_enabled: bool | None = None
    coffee_invitations_enabled: bool | None = None
    previous_details: RegistrationDetails | None = None

    def target_for_current_message(
        self,
        message_profile: TelegramProfile | None,
    ) -> TelegramProfile:
        if (
            message_profile is not None
            and message_profile.telegram_user_id == self.target.telegram_user_id
        ):
            return message_profile
        return self.target

    def require_display_name(self) -> str:
        if self.requested_display_name is None:
            raise RuntimeError("Registration flow has no requested display name")
        return self.requested_display_name
