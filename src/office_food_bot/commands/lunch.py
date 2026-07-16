from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.commanding.access import CommandAccessService
from office_food_bot.commanding.contracts import (
    CommandContext,
    EffectCommand,
)
from office_food_bot.commanding.definition import (
    CommandDefinition,
    CommandHelpEntry,
    CommandInputMessage,
    CommandScope,
    HelpSection,
)
from office_food_bot.commanding.errors.models import (
    CommonErrorCode,
    InputErrorCode,
)
from office_food_bot.commanding.errors.rendering import ErrorRenderer
from office_food_bot.commanding.validators import (
    ActiveUserValidator,
    TelegramIdentityValidator,
    require_telegram_profile,
)
from office_food_bot.execution import CommandExecutionMode
from office_food_bot.invitation_models import InvitationKind
from office_food_bot.messaging import BotMessenger
from office_food_bot.presenters.invitations import render_invitation_setting
from office_food_bot.result import Result, failure, success
from office_food_bot.services.invitations import InvitationPreferenceService
from office_food_bot.services.lunch_auto import LunchPollPublisher
from office_food_bot.services.lunch_polls import (
    LunchOfficeSelection,
    parse_lunch_office_selection,
)
from office_food_bot.services.user_access import ActiveUserResolver

INVALID_LUNCH_OFFICE_MESSAGE = (
    "Не понял офис. Используй /lunch, /lunch rose, /lunch роза, "
    "/lunch skyline или /lunch скайлайн."
)


@dataclass(frozen=True, slots=True)
class LunchRequest:
    pass


@dataclass(frozen=True, slots=True)
class LunchDefaultRequest(LunchRequest):
    pass


@dataclass(frozen=True, slots=True)
class LunchToggleRequest(LunchRequest):
    enabled: bool


@dataclass(frozen=True, slots=True)
class LunchPublishRequest(LunchRequest):
    office_selection: LunchOfficeSelection


class LunchRequestParser:
    def parse(
        self,
        raw_arguments: str | None,
    ) -> Result[LunchRequest, InputErrorCode]:
        argument = (raw_arguments or "").strip().casefold()
        if not argument:
            return success(LunchDefaultRequest())
        if argument in {"on", "off"}:
            return success(LunchToggleRequest(argument == "on"))
        office_selection = parse_lunch_office_selection(argument)
        if office_selection is None:
            return failure(InputErrorCode.INVALID_CHOICE)
        return success(LunchPublishRequest(office_selection))


class LunchPublishValidator:
    def __init__(
        self,
        access: CommandAccessService,
    ) -> None:
        self._access = access

    def validate(
        self,
        context: CommandContext,
        request: LunchRequest,
    ) -> Result[None, CommonErrorCode]:
        if isinstance(request, LunchToggleRequest):
            return success(None)
        profile = require_telegram_profile(context)
        can_publish = self._access.can_run_group_command_in_chat(
            str(context.message.chat.type),
            profile.telegram_user_id,
        )
        if isinstance(request, LunchPublishRequest) and not can_publish:
            return failure(CommonErrorCode.GROUP_CHAT_REQUIRED)
        return success(None)


class LunchCommand(EffectCommand[LunchRequest]):
    definition = CommandDefinition(
        "lunch",
        "создать опрос про обед",
        "/lunch [rose|роза|skyline|скайлайн]",
        CommandScope.ANY,
        HelpSection.MAIN,
        help_scope=CommandScope.GROUP,
        additional_help=(
            CommandHelpEntry(
                "/lunch",
                "показать настройки приглашений на ланч",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.PRIVATE,
            ),
            CommandHelpEntry(
                "/lunch on",
                "включить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
            CommandHelpEntry(
                "/lunch off",
                "выключить приглашения",
                HelpSection.PROFILE_SETTINGS,
                CommandScope.ANY,
            ),
        ),
        private_description="настроить приглашения на ланч",
        input_errors=(
            CommandInputMessage(
                InputErrorCode.INVALID_CHOICE,
                INVALID_LUNCH_OFFICE_MESSAGE,
            ),
        ),
    )

    def __init__(
        self,
        messenger: BotMessenger,
        common_error_renderer: ErrorRenderer[CommonErrorCode],
        access: CommandAccessService,
        invitations: InvitationPreferenceService,
        active_users: ActiveUserResolver,
        publisher: LunchPollPublisher,
    ) -> None:
        super().__init__(
            messenger,
            common_error_renderer,
            LunchRequestParser(),
            (TelegramIdentityValidator(),),
            (
                LunchPublishValidator(access),
                ActiveUserValidator(active_users),
            ),
        )
        self._access = access
        self._invitations = invitations
        self._publisher = publisher

    async def execute_effect(
        self,
        context: CommandContext,
        request: LunchRequest,
    ) -> None:
        profile = require_telegram_profile(context)

        if isinstance(request, LunchToggleRequest):
            await self._messenger.reply(
                context.message,
                render_invitation_setting(
                    self._invitations.set_enabled(
                        profile.telegram_user_id,
                        InvitationKind.LUNCH,
                        request.enabled,
                    )
                ),
            )
            return

        if isinstance(request, LunchDefaultRequest) and not (
            self._access.can_run_group_command_in_chat(
                str(context.message.chat.type),
                profile.telegram_user_id,
            )
        ):
            await self._messenger.reply(
                context.message,
                render_invitation_setting(
                    self._invitations.status(
                        profile.telegram_user_id,
                        InvitationKind.LUNCH,
                    )
                ),
            )
            return

        office_selection = LunchOfficeSelection.AUTOMATIC
        if isinstance(request, LunchPublishRequest):
            office_selection = request.office_selection
        elif not isinstance(request, LunchDefaultRequest):
            raise RuntimeError(f"Unsupported lunch request: {type(request).__name__}")

        await self._publisher.publish(
            context.bot,
            context.message.chat.id,
            mode=CommandExecutionMode.MANUAL,
            office_selection=office_selection,
        )
