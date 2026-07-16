from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiogram.types import Message, TelegramObject

from office_food_bot.commanding.catalog import CommandCatalog
from office_food_bot.commanding.errors.models import UserFacingError
from office_food_bot.commanding.errors.rendering import (
    CommandErrorRenderer,
    ErrorRenderer,
)
from office_food_bot.commanding.invocation import parse_command
from office_food_bot.messaging import BotMessenger


class UserFacingErrorMiddleware:
    def __init__(
        self,
        catalog: CommandCatalog,
        renderer: ErrorRenderer,
        messenger: BotMessenger,
    ) -> None:
        self._catalog = catalog
        self._renderer = renderer
        self._messenger = messenger

    async def __call__[MiddlewareDataT](
        self,
        handler: Callable[
            [TelegramObject, MiddlewareDataT],
            Awaitable[TelegramObject | None],
        ],
        event: TelegramObject,
        data: MiddlewareDataT,
    ) -> TelegramObject | None:
        try:
            return await handler(event, data)
        except UserFacingError as error:
            if not isinstance(event, Message):
                raise
            parsed = parse_command(event.text)
            command = None if parsed is None else self._catalog.resolve(parsed.name)
            renderer: ErrorRenderer = self._renderer
            if command is not None:
                renderer = CommandErrorRenderer(renderer, command.definition)
            await self._messenger.reply(
                event,
                renderer.render(error),
            )
            return None
