from __future__ import annotations

from office_food_bot.features.invitations.service import InvitationPreferenceService
from office_food_bot.features.registration.flow.flow import RegistrationFlow
from office_food_bot.features.registration.flow.steps.coffee_preference import (
    RegistrationCoffeePreferenceStep,
)
from office_food_bot.features.registration.flow.steps.lunch_preference import (
    RegistrationLunchPreferenceStep,
)
from office_food_bot.features.registration.flow.steps.name import RegistrationNameStep
from office_food_bot.features.registration.flow.steps.reregistration import (
    RegistrationConfirmationStep,
)
from office_food_bot.features.registration.flow.steps.splitwise import RegistrationSplitwiseStep
from office_food_bot.features.registration.flow.use_case import RegistrationFlowUseCase
from office_food_bot.features.registration.flow.validation import (
    CoffeePreferenceValidator,
    LunchPreferenceValidator,
    RegistrationNameValidator,
    ReregistrationDecisionValidator,
    SplitwiseAnswerValidator,
    TextFlowInputParser,
)
from office_food_bot.features.registration.service import RegistrationService
from office_food_bot.integrations.splitwise import SplitwiseService


def build_registration_flow(
    registration: RegistrationService,
    invitations: InvitationPreferenceService,
    splitwise: SplitwiseService,
) -> RegistrationFlow:
    use_case = RegistrationFlowUseCase(registration, invitations)
    return RegistrationFlow(
        registration,
        (
            RegistrationNameStep(
                TextFlowInputParser(),
                (RegistrationNameValidator(),),
                registration,
            ),
            RegistrationSplitwiseStep(
                TextFlowInputParser(),
                (SplitwiseAnswerValidator(),),
                registration,
                splitwise,
                use_case,
            ),
            RegistrationLunchPreferenceStep(
                TextFlowInputParser(),
                (LunchPreferenceValidator(),),
            ),
            RegistrationCoffeePreferenceStep(
                TextFlowInputParser(),
                (CoffeePreferenceValidator(),),
                use_case,
            ),
            RegistrationConfirmationStep(
                TextFlowInputParser(),
                (ReregistrationDecisionValidator(),),
                use_case,
            ),
        ),
    )
