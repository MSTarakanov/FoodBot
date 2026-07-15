from __future__ import annotations

import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent, Message, Update

from office_food_bot.commanding.errors.models import CommonError, CommonErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderContext, UserErrorRenderer
from office_food_bot.messaging import BotMessenger
from office_food_bot.services import BotServices

UNHANDLED_ERROR_REPLY_TEXT = "Произошла ошибка. Попробуй позже."

logger = logging.getLogger(__name__)


async def unhandled_error_handler(
    event: ErrorEvent,
    messenger: BotMessenger,
    services: BotServices,
    user_error_renderer: UserErrorRenderer,
) -> bool:
    exception = event.exception
    logger.error(
        "Unhandled error while processing Telegram update",
        exc_info=exception,
    )

    message = _message_from_update(event.update)
    if message is None:
        return True

    try:
        await messenger.reply(
            message,
            user_error_renderer.render(
                CommonError(CommonErrorCode.INTERNAL),
                ErrorRenderContext(services.telegram_bot_username, None),
            ),
        )
    except TelegramAPIError:
        logger.warning("Failed to notify user about unhandled error", exc_info=True)

    return True


def _message_from_update(update: Update) -> Message | None:
    return update.message
