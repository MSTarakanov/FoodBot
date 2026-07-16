from __future__ import annotations

from dataclasses import dataclass, replace

from office_food_bot.flows.contracts import (
    ClosingFlowView,
    CompleteFlow,
    FlowContext,
    FlowPostAction,
    FlowTransition,
    MoveToStep,
)
from office_food_bot.flows.registration.draft import RegistrationDraft
from office_food_bot.flows.registration.identifiers import RegistrationStepId
from office_food_bot.flows.registration.rendering import (
    admin_registration_text,
    registration_details_changed,
    registration_details_from_input,
    registration_details_from_user,
    registration_reply_text,
    reregistration_confirmation_view,
    unchanged_registration_view,
)
from office_food_bot.models import (
    InvitationPreferences,
    RegisteredUser,
    RegistrationDetails,
    RegistrationKind,
    SplitwiseMember,
)
from office_food_bot.services.invitations import InvitationPreferenceService
from office_food_bot.services.registration import RegistrationService


@dataclass(frozen=True, slots=True)
class RegistrationAdminNotification(FlowPostAction):
    admin_ids: frozenset[int]
    registered_user: RegisteredUser
    title: str
    splitwise_member: SplitwiseMember | None
    previous_details: RegistrationDetails | None
    preferences: InvitationPreferences | None = None

    async def execute(self, context: FlowContext) -> None:
        current_details = registration_details_from_user(
            self.registered_user,
            self.splitwise_member,
        )
        for admin_id in self.admin_ids:
            await context.messenger.try_send(
                context.bot,
                admin_id,
                admin_registration_text(
                    self.title,
                    telegram_user_id=self.registered_user.telegram_user_id,
                    current_details=current_details,
                    previous_details=self.previous_details,
                    preferences=self.preferences,
                ),
            )


class RegistrationFlowUseCase:
    def __init__(
        self,
        registration: RegistrationService,
        invitations: InvitationPreferenceService,
    ) -> None:
        self._registration = registration
        self._invitations = invitations

    async def complete(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
    ) -> FlowTransition:
        profile = draft.target_for_current_message(context.profile)
        display_name = draft.require_display_name()
        splitwise_member = draft.splitwise_member
        preferences = _preferences_from_draft(draft)
        result = self._registration.register(
            profile,
            display_name,
            splitwise_member,
        )

        if preferences is not None and result.kind == RegistrationKind.CREATED:
            self._invitations.save_initial(result.user.id, preferences)

        if result.kind == RegistrationKind.CREATED:
            return CompleteFlow(
                ClosingFlowView(
                    registration_reply_text(
                        "Заявка на регистрацию отправлена. Жду аппрув.",
                        splitwise_member,
                        preferences,
                    )
                ),
                RegistrationAdminNotification(
                    self._registration.admin_ids,
                    result.user,
                    "Новая регистрация:",
                    splitwise_member,
                    None,
                    preferences,
                ),
            )

        if result.kind == RegistrationKind.UPDATED_PENDING:
            return CompleteFlow(
                ClosingFlowView(
                    registration_reply_text(
                        "Заявка обновлена. Жду аппрув.",
                        splitwise_member,
                    )
                ),
                RegistrationAdminNotification(
                    self._registration.admin_ids,
                    result.user,
                    "Обновленная регистрация:",
                    splitwise_member,
                    result.previous_details,
                ),
            )

        if result.kind == RegistrationKind.ALREADY_ACTIVE:
            previous_details = result.previous_details or RegistrationDetails(
                display_name=result.user.display_name,
                splitwise=None,
            )
            requested_details = registration_details_from_input(
                self._registration,
                profile,
                display_name,
                splitwise_member,
            )
            if not registration_details_changed(previous_details, requested_details):
                return CompleteFlow(unchanged_registration_view())

            requested_display_name = self._registration.display_name_from_input(
                profile,
                display_name,
            )
            return MoveToStep(
                RegistrationStepId.REREGISTRATION_CONFIRMATION,
                replace(
                    draft,
                    target=profile,
                    requested_display_name=requested_display_name,
                    previous_details=previous_details,
                ),
                reregistration_confirmation_view(
                    result.user,
                    requested_display_name,
                    splitwise_member,
                    previous_details,
                ),
            )

        if result.kind == RegistrationKind.ALREADY_PENDING:
            return CompleteFlow(
                ClosingFlowView(f"Заявка уже ждет аппрува, {result.user.display_name}")
            )

        return CompleteFlow(
            ClosingFlowView(
                f"Регистрация сейчас недоступна, {result.user.display_name}"
            )
        )

    async def confirm_reregistration(
        self,
        context: FlowContext,
        draft: RegistrationDraft,
        *,
        confirmed: bool,
    ) -> FlowTransition:
        if not confirmed:
            return CompleteFlow(ClosingFlowView("Оставил текущую регистрацию."))

        profile = draft.target_for_current_message(context.profile)
        display_name = draft.require_display_name()
        splitwise_member = draft.splitwise_member
        user = self._registration.re_register(
            profile,
            display_name,
            splitwise_member,
        )
        return CompleteFlow(
            ClosingFlowView(
                registration_reply_text(
                    "Заявка на перерегистрацию отправлена. Жду аппрув.",
                    splitwise_member,
                )
            ),
            RegistrationAdminNotification(
                self._registration.admin_ids,
                user,
                "Перерегистрация:",
                splitwise_member,
                draft.previous_details,
            ),
        )


def _preferences_from_draft(
    draft: RegistrationDraft,
) -> InvitationPreferences | None:
    if (
        draft.lunch_invitations_enabled is None
        or draft.coffee_invitations_enabled is None
    ):
        return None
    return InvitationPreferences(
        draft.lunch_invitations_enabled,
        draft.coffee_invitations_enabled,
    )
