from __future__ import annotations

from office_food_bot.commanding.contracts import (
    CommandContext,
    RenderedCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandInputMessage,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import CommonErrorCode, InputErrorCode
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.commands.presence import (
    MAX_ETA_MINUTES,
    EtaInput,
    EtaRequestParser,
    EtaRequestResolver,
)
from office_food_bot.features.presence.models import EtaRequest, PresenceKind, PresenceReport
from office_food_bot.features.presence.rendering import render_presence_report
from office_food_bot.features.presence.service import PresenceService
from office_food_bot.features.users.access import ActiveUserResolver
from office_food_bot.messaging import BotMessenger


class EtaCommand(RenderedCommand[EtaInput, EtaRequest, PresenceReport]):
    definition = CommandDefinition(
        "eta",
        "сообщить ожидаемое время доставки",
        "/eta 20 или /eta 20-30",
        CommandScope.GROUP,
        HelpSection.MAIN,
        input_errors=(
            CommandInputMessage(
                InputErrorCode.MISSING,
                "Напиши через сколько минут или диапазон: /eta 20 или /eta 20-30",
            ),
            CommandInputMessage(
                InputErrorCode.INVALID_FORMAT,
                "Минуты должны быть числом или диапазоном: /eta 20 или /eta 20-30",
            ),
            CommandInputMessage(
                InputErrorCode.OUT_OF_RANGE,
                f"Минуты должны быть от 0 до {MAX_ETA_MINUTES} (366 дней): "
                "/eta 20 или /eta 20-30",
            ),
            CommandInputMessage(
                InputErrorCode.REVERSED_RANGE,
                "Начало диапазона должно быть не больше конца: /eta 20-30",
            ),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        presence: PresenceService,
        active_users: ActiveUserResolver,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            EtaRequestParser(),
            (
                TelegramIdentityValidator(),
                ActiveUserValidator(active_users),
            ),
            (),
            EtaRequestResolver(),
            render_presence_report,
        )
        self._presence = presence

    async def execute(
        self,
        context: CommandContext,
        request: EtaRequest,
    ) -> PresenceReport:
        profile = require_telegram_profile(context)
        return self._presence.report(
            profile.telegram_user_id,
            request,
            PresenceKind.DELIVERY_ETA,
        )
