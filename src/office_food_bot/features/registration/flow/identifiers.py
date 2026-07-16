from enum import auto

from office_food_bot.flows.contracts import FlowId, FlowStepId


class RegistrationFlowId(FlowId):
    REGISTRATION = auto()


class RegistrationStepId(FlowStepId):
    NAME = auto()
    SPLITWISE = auto()
    LUNCH_PREFERENCE = auto()
    COFFEE_PREFERENCE = auto()
    REREGISTRATION_CONFIRMATION = auto()
