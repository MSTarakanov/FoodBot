from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart

from office_food_bot.commands.approve import approve_command
from office_food_bot.commands.balance import balance_command
from office_food_bot.commands.hi import hi_command
from office_food_bot.commands.meta import meta_command
from office_food_bot.commands.register import register_command
from office_food_bot.commands.start import start_command


def create_command_router() -> Router:
    router = Router(name="commands")
    router.message.register(start_command, CommandStart())
    router.message.register(hi_command, Command("hi"))
    router.message.register(register_command, Command("register"))
    router.message.register(approve_command, Command("approve"))
    router.message.register(meta_command, Command("meta"))
    router.message.register(balance_command, Command("balance"))
    return router
