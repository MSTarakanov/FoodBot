from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart

from office_food_bot.commands.approve import approve_command
from office_food_bot.commands.balance import balance_command
from office_food_bot.commands.help import help_command
from office_food_bot.commands.hi import hi_command
from office_food_bot.commands.lunch import lunch_command
from office_food_bot.commands.meta import meta_command
from office_food_bot.commands.poll_tracking import poll_answer_handler
from office_food_bot.commands.register import (
    RegistrationFlow,
    cancel_registration_command,
    confirm_reregistration_message,
    confirm_reregistration_unknown_message,
    register_command,
    register_name_message,
    register_splitwise_email_message,
    registration_waiting_for_name_unknown_message,
    registration_waiting_for_splitwise_unknown_message,
)
from office_food_bot.commands.register_requests_list import register_requests_list_command
from office_food_bot.commands.start import start_command


def create_command_router() -> Router:
    router = Router(name="commands")
    router.message.register(cancel_registration_command, Command("cancel"))
    router.message.register(start_command, CommandStart())
    router.message.register(help_command, Command("help"))
    router.message.register(hi_command, Command("hi"))
    router.message.register(register_command, Command("register"))
    router.message.register(approve_command, Command("approve"))
    router.message.register(register_requests_list_command, Command("register_requests_list"))
    router.message.register(meta_command, Command("meta"))
    router.message.register(balance_command, Command("balance"))
    router.message.register(lunch_command, Command("lunch"))
    router.poll_answer.register(poll_answer_handler)
    router.message.register(register_name_message, RegistrationFlow.waiting_for_name, F.text)
    router.message.register(
        register_splitwise_email_message,
        RegistrationFlow.waiting_for_splitwise_email,
        F.text,
    )
    router.message.register(
        confirm_reregistration_message,
        RegistrationFlow.confirming_reregistration,
        F.text,
    )
    router.message.register(
        confirm_reregistration_unknown_message,
        RegistrationFlow.confirming_reregistration,
    )
    router.message.register(
        registration_waiting_for_name_unknown_message,
        RegistrationFlow.waiting_for_name,
    )
    router.message.register(
        registration_waiting_for_splitwise_unknown_message,
        RegistrationFlow.waiting_for_splitwise_email,
    )
    return router
