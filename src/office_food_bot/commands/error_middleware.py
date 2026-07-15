from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiogram.types import Message, TelegramObject

from office_food_bot.commands.catalog import CommandCatalog
from office_food_bot.commands.error_rendering import ErrorRenderContext, UserErrorRenderer
from office_food_bot.commands.parsing import parse_command
from office_food_bot.messaging import BotMessenger
from office_food_bot.user_errors import UserFacingError


class UserFacingErrorMiddleware:
    def __init__(
        self,
        catalog: CommandCatalog,
        renderer: UserErrorRenderer,
        messenger: BotMessenger,
        bot_username: str,
    ) -> None:
        self._catalog = catalog
        self._renderer = renderer
        self._messenger = messenger
        self._bot_username = bot_username

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
            definition = None if command is None else command.definition
            await self._messenger.reply(
                event,
                self._renderer.render(
                    error,
                    ErrorRenderContext(self._bot_username, definition),
                ),
            )
            return None
