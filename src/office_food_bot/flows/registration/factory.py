from __future__ import annotations

from office_food_bot.flows.registration.flow import RegistrationFlow
from office_food_bot.flows.registration.steps.coffee_preference import (
    RegistrationCoffeePreferenceStep,
)
from office_food_bot.flows.registration.steps.lunch_preference import (
    RegistrationLunchPreferenceStep,
)
from office_food_bot.flows.registration.steps.name import RegistrationNameStep
from office_food_bot.flows.registration.steps.reregistration import (
    RegistrationConfirmationStep,
)
from office_food_bot.flows.registration.steps.splitwise import RegistrationSplitwiseStep
from office_food_bot.flows.registration.use_case import RegistrationFlowUseCase
from office_food_bot.flows.registration.validation import (
    CoffeePreferenceValidator,
    LunchPreferenceValidator,
    RegistrationNameValidator,
    ReregistrationDecisionValidator,
    SplitwiseAnswerValidator,
    TextFlowInputParser,
)
from office_food_bot.services.invitations import InvitationPreferenceService
from office_food_bot.services.registration import RegistrationService
from office_food_bot.services.splitwise import SplitwiseService


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
