from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    GetMe,
    PinChatMessage,
    SendPoll,
    SetMyCommands,
    TelegramMethod,
    UnpinChatMessage,
)
from aiogram.methods.base import TelegramType
from aiogram.methods.send_message import SendMessage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    BotCommandScopeUnion,
    CallbackQuery,
    Chat,
    InlineKeyboardMarkup,
    Message,
    Poll,
    PollAnswer,
    ReplyKeyboardMarkup,
    Update,
    User,
)
from aiogram.types import PollOption as TelegramPollOption

from office_food_bot.app import create_dispatcher, create_services
from office_food_bot.coffee_repositories import CoffeeSessionRepository
from office_food_bot.commands.definitions import COMMANDS, START_TEXT
from office_food_bot.commands.errors import UNHANDLED_ERROR_REPLY_TEXT
from office_food_bot.commands.menu import setup_bot_commands
from office_food_bot.config import RuntimeEnvironment, Settings
from office_food_bot.database import Database
from office_food_bot.invitation_repositories import InvitationPreferenceRepository
from office_food_bot.message_previews import MESSAGE_PREVIEWS
from office_food_bot.models import (
    CoffeeSessionStatus,
    InvitationPreferences,
    PollKind,
    SplitwiseBalance,
    SplitwiseMember,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.poll_options import PollOption
from office_food_bot.repositories import (
    LunchAutoChatRepository,
    LunchPinRepository,
    RegistrationRequestRepository,
    TelegramAccountRepository,
    UserRepository,
    VacationRepository,
)
from office_food_bot.services import BotServices
from office_food_bot.services.lunch_polls import (
    LUNCH_OTHER_FOOD_POLL,
    ROSE_LUNCH_POLLS,
    SKYLINE_LUNCH_POLLS,
    OfficeLunchPolls,
)
from office_food_bot.services.splitwise import SplitwiseUnavailableError

DEFAULT_ADMIN_IDS = frozenset({7})
DEFAULT_SPLITWISE_GROUP_ID = 55
ROSE_OTHER_OPTION_INDEX = tuple(
    ROSE_LUNCH_POLLS.place.options
).index(
    PollOption.LUNCH_PLACE_OTHER
)
PRIVATE_HELP_TEXT = (
    "<b>Команды:</b>\n\n"
    "<b>Основные:</b>\n"
    "/balance - показать баланс Splitwise\n\n"
    "<b>Профиль и настройки:</b>\n"
    "/register - пройти регистрацию\n"
    "/request_register - попросить админа зарегистрировать вас\n"
    "/quit - отрегистрироваться\n"
    "/lunch - показать настройки приглашений на ланч\n"
    "/lunch on - включить приглашения\n"
    "/lunch off - выключить приглашения\n"
    "/coffee (также /кофе) - показать настройки приглашений на кофе\n"
    "/coffee on (также /кофе on) - включить приглашения\n"
    "/coffee off (также /кофе off) - выключить приглашения\n\n"
    "<b>Служебные:</b>\n"
    "/start - показать приветствие\n"
    "/help - показать список команд\n"
    "/hi - проверить, что бот на месте\n"
    "/cancel - отменить текущий сценарий"
)
ADMIN_PRIVATE_HELP_TEXT = (
    "<b>Команды:</b>\n\n"
    "<b>Основные:</b>\n"
    "/balance - показать баланс Splitwise\n\n"
    "<b>Профиль и настройки:</b>\n"
    "/register - пройти регистрацию\n"
    "/request_register - попросить админа зарегистрировать вас\n"
    "/quit - отрегистрироваться\n"
    "/lunch - показать настройки приглашений на ланч\n"
    "/lunch on - включить приглашения\n"
    "/lunch off - выключить приглашения\n"
    "/coffee (также /кофе) - показать настройки приглашений на кофе\n"
    "/coffee on (также /кофе on) - включить приглашения\n"
    "/coffee off (также /кофе off) - выключить приглашения\n\n"
    "<b>Администрирование:</b>\n"
    "/approve 123456789 - подтвердить регистрацию\n"
    "/register_requests_list - показать заявки на регистрацию\n"
    "/debug 1 - включить или выключить debug режим\n"
    "/test balance-full - отправить тестовое сообщение\n\n"
    "<b>Служебные:</b>\n"
    "/start - показать приветствие\n"
    "/help - показать список команд\n"
    "/hi - проверить, что бот на месте\n"
    "/cancel - отменить текущий сценарий"
)
GROUP_HELP_MAIN_AND_SETTINGS = (
    "<b>Команды:</b>\n\n"
    "<b>Основные:</b>\n"
    "/meta 25 или /meta 20-30 - сообщить, через сколько минут или в каком диапазоне придешь\n"
    "/eta 20 или /eta 20-30 - сообщить ожидаемое время доставки\n"
    "/balance - показать баланс Splitwise\n"
    "/lunch [rose|роза|skyline|скайлайн] - создать опрос про обед\n"
    "/coffee 15 или /coffee 16:30 "
    "(также /кофе 15 или /кофе 16:30) - позвать на кофе\n\n"
    "<b>Профиль и настройки:</b>\n"
    "/request_register - попросить админа зарегистрировать вас\n"
    "/vacation - показать статус отпуска\n"
    "/vacation 2 или /vacation 20.07 - уйти в отпуск\n"
    "/vacation 0 или /vacation off - выйти из отпуска\n"
    "/lunch on - включить приглашения\n"
    "/lunch off - выключить приглашения\n"
    "/coffee on (также /кофе on) - включить приглашения\n"
    "/coffee off (также /кофе off) - выключить приглашения"
)
GROUP_HELP_SERVICE = (
    "<b>Служебные:</b>\n"
    "/help - показать список команд\n"
    "/hi - проверить, что бот на месте"
)
GROUP_HELP_TEXT = GROUP_HELP_MAIN_AND_SETTINGS + "\n\n" + GROUP_HELP_SERVICE
ADMIN_GROUP_HELP_TEXT = (
    GROUP_HELP_MAIN_AND_SETTINGS
    + "\n\n<b>Автоматизация:</b>\n"
    + "/lunch_auto_on - включить авто-ланч в этом чате\n"
    + "/lunch_auto_off - выключить авто-ланч в этом чате\n"
    + "/lunch_auto_status - показать статус авто-ланча\n\n"
    + GROUP_HELP_SERVICE
)


@dataclass(frozen=True)
class CommandMenu:
    scope_name: str
    chat_id: int | None
    commands: tuple[BotCommand, ...]


class RecordingSession(BaseSession):
    def __init__(
        self,
        failed_method_names: frozenset[str] = frozenset(),
    ) -> None:
        super().__init__()
        self._failed_method_names = failed_method_names
        self._failed_send_messages = 0
        self.sent_messages: list[SendMessage] = []
        self.sent_polls: list[SendPoll] = []
        self.sent_poll_ids: list[str] = []
        self.pin_requests: list[PinChatMessage] = []
        self.unpin_requests: list[UnpinChatMessage] = []
        self.set_command_requests: list[SetMyCommands] = []
        self.edited_messages: list[EditMessageText] = []
        self.callback_answers: list[AnswerCallbackQuery] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        if type(method).__name__ in self._failed_method_names:
            raise TelegramBadRequest(method=method, message="Bad Request")
        if isinstance(method, SendMessage) and self._failed_send_messages:
            self._failed_send_messages -= 1
            raise TelegramBadRequest(method=method, message="Bad Request")

        if isinstance(method, SendMessage):
            self.sent_messages.append(method)
            return _send_message_response(method, len(self.sent_messages) + len(self.sent_polls))
        if isinstance(method, SendPoll):
            self.sent_polls.append(method)
            message = _send_poll_response(method, len(self.sent_messages) + len(self.sent_polls))
            if message.poll is None:
                raise AssertionError("Expected fake sendPoll response to include poll")
            self.sent_poll_ids.append(message.poll.id)
            return message
        if isinstance(method, EditMessageText):
            self.edited_messages.append(method)
            return Message(
                message_id=method.message_id or 1,
                date=datetime.now(tz=UTC),
                chat=Chat(id=int(method.chat_id or -100), type="group"),
                text=method.text,
            )
        if isinstance(method, AnswerCallbackQuery):
            self.callback_answers.append(method)
            return True
        if isinstance(method, PinChatMessage):
            self.pin_requests.append(method)
            return True
        if isinstance(method, UnpinChatMessage):
            self.unpin_requests.append(method)
            return True
        if isinstance(method, GetMe):
            return User(
                id=123456,
                is_bot=True,
                first_name="FoodBot",
                username="foodbot_dev",
            )
        if isinstance(method, SetMyCommands):
            self.set_command_requests.append(method)
            return True

        raise AssertionError(f"Unexpected Telegram method: {type(method).__name__}")

    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        raise AssertionError("No streaming calls are expected in command tests")
        yield b""

    def clear_messages(self) -> None:
        self.sent_messages.clear()
        self.sent_polls.clear()
        self.sent_poll_ids.clear()
        self.pin_requests.clear()
        self.unpin_requests.clear()
        self.edited_messages.clear()
        self.callback_answers.clear()

    def fail_methods(self, *method_names: str) -> None:
        self._failed_method_names = frozenset(method_names)

    def fail_next_send_message(self) -> None:
        self._failed_send_messages += 1


class RecordingCommandMenuClient:
    def __init__(self) -> None:
        self.command_menus: list[CommandMenu] = []

    async def set_my_commands(
        self,
        commands: list[BotCommand],
        scope: BotCommandScopeUnion | None = None,
    ) -> bool:
        self.command_menus.append(_command_menu(scope, tuple(commands)))
        return True


class AdminChatNotFoundCommandMenuClient(RecordingCommandMenuClient):
    async def set_my_commands(
        self,
        commands: list[BotCommand],
        scope: BotCommandScopeUnion | None = None,
    ) -> bool:
        if isinstance(scope, BotCommandScopeChat):
            raise TelegramBadRequest(
                method=SetMyCommands(commands=commands, scope=scope),
                message="Bad Request: chat not found",
            )

        return await super().set_my_commands(commands, scope)


def _command_menu(
    scope: BotCommandScopeUnion | None,
    commands: tuple[BotCommand, ...],
) -> CommandMenu:
    if scope is None or isinstance(scope, BotCommandScopeDefault):
        return CommandMenu("default", None, commands)

    if isinstance(scope, BotCommandScopeAllPrivateChats):
        return CommandMenu("all_private", None, commands)

    if isinstance(scope, BotCommandScopeAllGroupChats):
        return CommandMenu("all_group", None, commands)

    if isinstance(scope, BotCommandScopeChat):
        chat_id = scope.chat_id
        if not isinstance(chat_id, int):
            raise AssertionError(f"Expected numeric admin chat id, got {chat_id!r}")
        return CommandMenu("chat", chat_id, commands)

    raise AssertionError(f"Unexpected command menu scope: {scope!r}")


class FakeSplitwiseClient:
    def __init__(
        self,
        members: tuple[SplitwiseMember, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self._members = members
        self._unavailable = unavailable

    async def group_members(self, group_id: int) -> tuple[SplitwiseMember, ...]:
        if group_id != DEFAULT_SPLITWISE_GROUP_ID:
            raise AssertionError(f"Unexpected Splitwise group id: {group_id}")
        if self._unavailable:
            raise SplitwiseUnavailableError("Splitwise is unavailable")
        return self._members


def _send_message_response(method: SendMessage, message_id: int) -> Message:
    chat_id = method.chat_id
    if not isinstance(chat_id, int):
        raise AssertionError(f"Expected numeric chat id, got {chat_id!r}")

    return Message(
        message_id=message_id,
        date=datetime.now(tz=UTC),
        chat=Chat(id=chat_id, type="private"),
        text=method.text,
    )


def _send_poll_response(method: SendPoll, message_id: int) -> Message:
    chat_id = method.chat_id
    if not isinstance(chat_id, int):
        raise AssertionError(f"Expected numeric chat id, got {chat_id!r}")

    return Message(
        message_id=message_id,
        date=datetime.now(tz=UTC),
        chat=Chat(id=chat_id, type="private"),
        poll=Poll(
            id=f"poll-{message_id}",
            question=method.question,
            options=[
                TelegramPollOption(
                    persistent_id=f"option-{message_id}-{option_index}",
                    text=option_text,
                    voter_count=0,
                )
                for option_index, option_text in enumerate(poll_option_texts(method))
            ],
            total_voter_count=0,
            is_closed=False,
            is_anonymous=bool(method.is_anonymous),
            type="regular",
            allows_multiple_answers=bool(method.allows_multiple_answers),
            allows_revoting=False,
            members_only=False,
        ),
    )


def make_update(
    text: str,
    user_id: int = 42,
    first_name: str = "Misha",
    username: str | None = "misha",
    last_name: str | None = None,
    chat_type: str = "private",
    chat_id: int | None = None,
    chat_title: str | None = None,
) -> Update:
    user = User(
        id=user_id,
        is_bot=False,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )
    resolved_chat_id = chat_id
    if resolved_chat_id is None:
        resolved_chat_id = user_id
    if chat_type != "private" and chat_id is None:
        resolved_chat_id = -100
    chat = Chat(id=resolved_chat_id, type=chat_type, title=chat_title)
    message = Message(
        message_id=100,
        date=datetime.now(tz=UTC),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=1, message=message)


def make_poll_answer_update(
    poll_id: str,
    option_ids: tuple[int, ...],
    user_id: int = 42,
    first_name: str = "Misha",
    username: str | None = "misha",
) -> Update:
    user = User(
        id=user_id,
        is_bot=False,
        first_name=first_name,
        username=username,
    )
    return Update(
        update_id=2,
        poll_answer=PollAnswer(
            poll_id=poll_id,
            option_ids=list(option_ids),
            option_persistent_ids=[
                f"{poll_id}-option-{option_id}"
                for option_id in option_ids
            ],
            user=user,
        ),
    )


def make_callback_update(
    data: str,
    user_id: int = 42,
    username: str | None = "misha",
) -> Update:
    return Update(
        update_id=3,
        callback_query=CallbackQuery(
            id="callback-1",
            from_user=User(
                id=user_id,
                is_bot=False,
                first_name="Misha",
                username=username,
            ),
            chat_instance="coffee-chat",
            data=data,
        ),
    )


def make_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    return database


def activate_user(
    database: Database,
    telegram_user_id: int,
    display_name: str,
    username: str | None,
) -> None:
    users = UserRepository(database)
    users.create_pending_user(
        TelegramProfile(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=display_name,
            last_name=None,
        ),
        display_name,
    )
    users.approve_by_telegram_id(telegram_user_id)


def make_test_services(
    database: Database,
    admin_ids: frozenset[int] = DEFAULT_ADMIN_IDS,
    splitwise_members: tuple[SplitwiseMember, ...] = (),
    splitwise_unavailable: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> BotServices:
    settings = Settings(
        environment=RuntimeEnvironment.DEVELOPMENT,
        telegram_bot_token="123456:test-token",
        telegram_bot_username="foodbot_dev",
        database_path=database.path,
        telegram_admin_ids=admin_ids,
        timezone="Europe/Belgrade",
        splitwise_api_key=None,
        splitwise_group_id=DEFAULT_SPLITWISE_GROUP_ID,
        production_telegram_bot_id=8490386710,
    )
    services = create_services(
        database,
        settings,
        clock=clock
        or (lambda: datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade"))),
        splitwise_client=FakeSplitwiseClient(
            splitwise_members,
            unavailable=splitwise_unavailable,
        ),
    )
    return services


def make_dispatcher(
    database: Database,
    admin_ids: frozenset[int] = DEFAULT_ADMIN_IDS,
    splitwise_members: tuple[SplitwiseMember, ...] = (),
    splitwise_unavailable: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> Dispatcher:
    services = make_test_services(
        database,
        admin_ids,
        splitwise_members,
        splitwise_unavailable,
        clock,
    )
    return create_dispatcher(services)


def sent_texts(session: RecordingSession) -> list[str]:
    return [message.text for message in session.sent_messages]


def _command_names(commands: tuple[BotCommand, ...]) -> list[str]:
    return [command.command for command in commands]


def keyboard_texts(message: SendMessage) -> list[list[str]]:
    reply_markup = message.reply_markup
    assert isinstance(reply_markup, ReplyKeyboardMarkup)
    return [[button.text for button in row] for row in reply_markup.keyboard]


def inline_callback_data(message: SendMessage) -> dict[str, str]:
    reply_markup = message.reply_markup
    assert isinstance(reply_markup, InlineKeyboardMarkup)
    return {
        button.text: button.callback_data or ""
        for row in reply_markup.inline_keyboard
        for button in row
    }


def poll_option_texts(poll: SendPoll) -> list[str]:
    texts: list[str] = []
    for option in poll.options:
        if isinstance(option, str):
            texts.append(option)
        else:
            texts.append(option.text)
    return texts


def make_splitwise_member(
    splitwise_user_id: int = 1001,
    email: str = "max@example.com",
    balance_amount: str | None = None,
) -> SplitwiseMember:
    balance: tuple[SplitwiseBalance, ...] = ()
    if balance_amount is not None:
        balance = (
            SplitwiseBalance(
                currency_code="RSD",
                amount=Decimal(balance_amount),
            ),
        )
    return SplitwiseMember(
        splitwise_user_id=splitwise_user_id,
        first_name="Max",
        last_name=None,
        email=email,
        balance=balance,
    )


async def submit_registration(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    *,
    user_id: int = 42,
    first_name: str = "Misha",
    username: str | None = "misha",
    display_name: str = "Максим",
    splitwise_answer: str = "Пропустить",
) -> None:
    await dispatcher.feed_update(
        bot,
        make_update("/register", user_id=user_id, first_name=first_name, username=username),
    )
    session.clear_messages()
    await dispatcher.feed_update(
        bot,
        make_update(display_name, user_id=user_id, first_name=first_name, username=username),
    )
    session.clear_messages()
    await dispatcher.feed_update(
        bot,
        make_update(splitwise_answer, user_id=user_id, first_name=first_name, username=username),
    )
    if sent_texts(session)[-1].endswith(
        "Звать тебя на ланч упоминанием в общем чате?"
    ):
        await dispatcher.feed_update(
            bot,
            make_update("Да", user_id=user_id, first_name=first_name, username=username),
        )
        session.clear_messages()
        await dispatcher.feed_update(
            bot,
            make_update("Да", user_id=user_id, first_name=first_name, username=username),
        )


@pytest.mark.parametrize(
    ("incoming_text", "expected_text"),
    [
        ("/start", START_TEXT),
        ("/help", PRIVATE_HELP_TEXT),
        ("/hi", "Привет! Я на месте."),
    ],
)
async def test_commands_reply_with_expected_text(
    incoming_text: str,
    expected_text: str,
    tmp_path: Path,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update(incoming_text))

    assert len(session.sent_messages) == 1
    request = session.sent_messages[0]
    assert request.chat_id == 42
    assert request.text == expected_text


async def test_hi_logs_bot_identity(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)
    caplog.set_level(logging.WARNING, logger="office_food_bot.commands.hi")

    await dispatcher.feed_update(
        bot,
        make_update("/hi", first_name="Misha", last_name="Petrov", username="misha"),
    )

    assert "/hi handled by @foodbot_dev: chat_id=42, telegram_user_id=42" in caplog.text
    assert UserRepository(database).get_by_telegram_id(42) is None
    telegram_account = TelegramAccountRepository(database).get(42)
    assert telegram_account is not None
    assert telegram_account.username == "misha"
    assert telegram_account.first_name == "Misha"
    assert telegram_account.last_name == "Petrov"
    assert RegistrationRequestRepository(database).list_requested(limit=10) == ()


async def test_command_updates_existing_telegram_profile(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)
    users = UserRepository(database)
    users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username=None,
            first_name="Telegram ID 42",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)

    await dispatcher.feed_update(
        bot,
        make_update("/hi", first_name="Misha", last_name="Petrov", username="misha"),
    )

    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.username == "misha"
    assert user.first_name == "Misha"
    assert user.last_name == "Petrov"


async def test_help_shows_admin_commands_to_admins(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/help", user_id=7, first_name="Admin"))

    assert sent_texts(session) == [ADMIN_PRIVATE_HELP_TEXT]
    assert session.sent_messages[0].parse_mode == ParseMode.HTML


async def test_admin_can_send_balance_preview_in_private_chat(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update("/test balance-full", user_id=7, first_name="Admin"),
    )

    expected = MESSAGE_PREVIEWS.render("balance-full")
    assert expected is not None
    assert len(session.sent_messages) == 1
    assert session.sent_messages[0].text == expected.text
    assert session.sent_messages[0].parse_mode == expected.parse_mode
    assert session.sent_messages[0].link_preview_options == expected.link_preview_options


@pytest.mark.parametrize("command", ["/test", "/test unknown"])
async def test_test_command_lists_available_cases(
    tmp_path: Path,
    command: str,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(command, user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == [MESSAGE_PREVIEWS.help_text()]


async def test_test_command_is_admin_only(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/test balance-full"))

    assert sent_texts(session) == ["Команда доступна только админам."]


async def test_test_command_is_private_only(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/test balance-full",
            user_id=7,
            first_name="Admin",
            chat_type="group",
        ),
    )

    assert sent_texts(session) == [
        "Команда доступна только в личке: https://t.me/foodbot_dev"
    ]


async def test_help_shows_group_commands_in_group_chat(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/help", chat_type="group"))

    assert sent_texts(session) == [GROUP_HELP_TEXT]


async def test_help_shows_group_admin_commands_to_admins_in_group_chat(
    tmp_path: Path,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update("/help", user_id=7, first_name="Admin", chat_type="group"),
    )

    assert sent_texts(session) == [ADMIN_GROUP_HELP_TEXT]


async def test_help_shows_all_sections_to_admin_in_private_debug(
    tmp_path: Path,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    services = make_test_services(database)
    services.debug.set_enabled(7, True)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/help", user_id=7, first_name="Admin"))

    help_message = sent_texts(session)[0]
    section_positions = tuple(
        help_message.index(f"<b>{section}:</b>")
        for section in (
            "Основные",
            "Профиль и настройки",
            "Автоматизация",
            "Администрирование",
            "Служебные",
        )
    )
    assert section_positions == tuple(sorted(section_positions))
    assert "/coffee 15 или /coffee 16:30" in help_message
    assert "/coffee on (также /кофе on)" in help_message
    assert "/lunch_auto_on" in help_message
    assert "/approve 123456789" in help_message


async def test_private_only_command_in_group_points_to_private_bot_link(
    tmp_path: Path,
) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register", chat_type="group"))

    assert sent_texts(session) == [
        "Команда доступна только в личке: https://t.me/foodbot_dev"
    ]
    assert UserRepository(database).get_by_telegram_id(42) is None


async def test_unhandled_command_error_replies_with_generic_message(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    async def broken_command(message: Message) -> None:
        msg = "secret internal detail"
        raise RuntimeError(msg)

    dispatcher.message.register(broken_command, Command("boom"))

    await dispatcher.feed_update(bot, make_update("/boom"))

    assert sent_texts(session) == [UNHANDLED_ERROR_REPLY_TEXT]


async def test_command_addressed_to_another_bot_is_ignored(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register@another_bot", chat_type="group"))

    assert sent_texts(session) == []
    assert UserRepository(database).get_by_telegram_id(42) is None


async def test_setup_bot_commands_registers_telegram_menu() -> None:
    database = Database(Path(":memory:"))
    database.init_schema()
    bot = RecordingCommandMenuClient()
    services = make_test_services(database)

    await setup_bot_commands(bot, services.command_access)

    assert len(bot.command_menus) == 4

    default_menu = bot.command_menus[0]
    assert default_menu.scope_name == "default"
    assert _command_names(default_menu.commands) == [
        "start",
        "help",
        "hi",
        "register",
        "quit",
        "cancel",
        "balance",
        "lunch",
        "coffee",
    ]

    private_menu = bot.command_menus[1]
    assert private_menu.scope_name == "all_private"
    assert _command_names(private_menu.commands) == [
        "start",
        "help",
        "hi",
        "register",
        "quit",
        "cancel",
        "balance",
        "lunch",
        "coffee",
    ]

    group_menu = bot.command_menus[2]
    assert group_menu.scope_name == "all_group"
    assert _command_names(group_menu.commands) == [
        "help",
        "hi",
        "meta",
        "eta",
        "balance",
        "vacation",
        "lunch",
        "coffee",
    ]
    vacation_menu_command = next(
        command for command in group_menu.commands if command.command == "vacation"
    )
    assert vacation_menu_command.description == "показать статус отпуска"
    assert "кофе" not in _command_names(group_menu.commands)

    admin_menu = bot.command_menus[3]
    assert admin_menu.scope_name == "chat"
    assert admin_menu.chat_id == 7
    assert _command_names(admin_menu.commands) == [
        "start",
        "help",
        "hi",
        "register",
        "quit",
        "cancel",
        "approve",
        "register_requests_list",
        "debug",
        "balance",
        "lunch",
        "coffee",
    ]

    database.close()


async def test_setup_bot_commands_uses_debug_menu_for_admin_chat() -> None:
    database = Database(Path(":memory:"))
    database.init_schema()
    bot = RecordingCommandMenuClient()
    services = make_test_services(database)
    services.debug.set_enabled(7, True)

    await setup_bot_commands(bot, services.command_access)

    admin_menu = bot.command_menus[3]
    assert admin_menu.scope_name == "chat"
    assert admin_menu.chat_id == 7
    assert _command_names(admin_menu.commands) == [
        definition.name for definition in COMMANDS if definition.show_in_menu
    ]

    database.close()


async def test_setup_bot_commands_ignores_missing_admin_chat() -> None:
    database = Database(Path(":memory:"))
    database.init_schema()
    bot = AdminChatNotFoundCommandMenuClient()
    services = make_test_services(database)

    await setup_bot_commands(bot, services.command_access)

    assert len(bot.command_menus) == 3
    assert [menu.scope_name for menu in bot.command_menus] == [
        "default",
        "all_private",
        "all_group",
    ]

    database.close()


async def test_register_creates_pending_user_and_notifies_admin(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    splitwise_member = make_splitwise_member()
    dispatcher = make_dispatcher(database, splitwise_members=(splitwise_member,))

    await dispatcher.feed_update(bot, make_update("/register"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("MAX@example.com"))

    assert sent_texts(session) == [
        "Splitwise найден: max@example.com (ID 1001).\n\n"
        "Звать тебя на ланч упоминанием в общем чате?"
    ]
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))

    texts = sent_texts(session)
    assert texts[0] == (
        "Заявка на регистрацию отправлена. Жду аппрув.\n\n"
            "Splitwise найден: max@example.com (ID 1001).\n\n"
            "Звать на ланч: да.\n"
            "Звать на кофе: да."
    )
    assert "Новая регистрация" in texts[1]
    assert "Имя: Максим" in texts[1]
    assert "Splitwise: max@example.com (ID 1001)" in texts[1]
    assert "Аппрув: /approve 42" in texts[1]

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Максим"
    assert user.status == UserStatus.PENDING
    pending_registrations = UserRepository(database).list_pending_registrations()
    assert pending_registrations[0].splitwise is not None
    assert pending_registrations[0].splitwise.email == "max@example.com"


async def test_register_with_argument_starts_step_by_step_flow(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))

    assert sent_texts(session) == [
        "Регистрация теперь пошаговая: имя нужно прислать отдельным сообщением.\n"
        "Напиши имя одним сообщением. Например: Максим\n"
        "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду."
    ]
    assert keyboard_texts(session.sent_messages[0]) == [["Misha"]]
    assert UserRepository(database).get_by_telegram_id(42) is None


async def test_request_register_notifies_admin_with_register_command(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/request_register",
            user_id=42,
            first_name="Misha",
            last_name="Petrov",
            username="misha",
        ),
    )

    assert sent_texts(session) == [
        "Запрос на регистрацию отправлен админам. "
        "Теперь администратор сможет зарегистрировать тебя.",
        "Запрос на регистрацию:\n"
        "Telegram ID: 42\n"
        "Username: @misha\n"
        "Имя в Telegram: Misha Petrov\n"
        "Начать регистрацию: /register 42",
    ]
    assert session.sent_messages[1].chat_id == 7
    assert UserRepository(database).get_by_telegram_id(42) is None
    telegram_account = TelegramAccountRepository(database).get(42)
    assert telegram_account is not None
    assert telegram_account.username == "misha"
    assert telegram_account.first_name == "Misha"
    assert telegram_account.last_name == "Petrov"
    assert [
        account.telegram_user_id
        for account in RegistrationRequestRepository(database).list_requested(limit=10)
    ] == [42]


async def test_lunch_tags_user_registered_from_request_register(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/request_register",
            user_id=42,
            first_name="Misha",
            last_name="Petrov",
            username="misha",
        ),
    )
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/register 42", user_id=7))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим", user_id=7))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить", user_id=7))
    await dispatcher.feed_update(bot, make_update("Да", user_id=7))
    await dispatcher.feed_update(bot, make_update("Да", user_id=7))
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7))
    session.clear_messages()

    assert RegistrationRequestRepository(database).list_requested(limit=10) == ()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert sent_texts(session)[0] == "Время обедать! @misha"


async def test_admin_register_requests_list_shows_seen_unregistered_users(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/hi",
            user_id=42,
            first_name="Misha",
            last_name="Petrov",
            username="misha",
        ),
    )
    session.clear_messages()

    await dispatcher.feed_update(
        bot,
        make_update("/register_requests_list", user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == [
        "Заявок на регистрацию нет.\n"
        "\n"
        "Видел незарегистрированных пользователей:\n"
        "1. Misha Petrov (@misha) - Telegram ID 42 - /register 42"
    ]


async def test_admin_register_requests_list_shows_requested_users(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/request_register",
            user_id=42,
            first_name="Misha",
            last_name="Petrov",
            username="misha",
        ),
    )
    session.clear_messages()

    await dispatcher.feed_update(
        bot,
        make_update("/register_requests_list", user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == [
        "Попросили регистрацию:\n"
        "1. Misha Petrov (@misha) - Telegram ID 42 - /register 42"
    ]


async def test_request_register_replies_when_user_is_already_pending(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/request_register"))

    assert sent_texts(session) == [
        "Заявка уже ждет аппрува. Если хотите отменить регистрацию, отправьте /quit."
    ]


async def test_request_register_replies_when_user_is_already_active(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/request_register"))

    assert sent_texts(session) == [
        "Вы уже зарегистрированы. Если хотите отрегистрироваться, отправьте /quit."
    ]


async def test_quit_unknown_user_replies_with_not_found(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/quit"))

    assert sent_texts(session) == ["Я не нашел вашу регистрацию."]


async def test_quit_marks_user_abandoned_and_removes_splitwise_link(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database, splitwise_members=(make_splitwise_member(),))

    await submit_registration(dispatcher, bot, session, splitwise_answer="max@example.com")
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/quit"))

    assert sent_texts(session) == [
        "Вы отрегистрированы. Если захотите вернуться, отправьте /request_register."
    ]
    users = UserRepository(database)
    user = users.get_by_telegram_id(42)
    assert user is not None
    assert user.status == UserStatus.ABANDONED
    assert users.list_active_splitwise_users() == ()
    details = users.get_registration_details_by_telegram_id(42)
    assert details is not None
    assert details.splitwise is None


async def test_request_register_after_quit_notifies_admin_again(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/quit"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/request_register"))

    assert sent_texts(session) == [
        "Запрос на регистрацию отправлен админам. "
        "Теперь администратор сможет зарегистрировать тебя.",
        "Запрос на регистрацию:\n"
        "Telegram ID: 42\n"
        "Username: @misha\n"
        "Имя в Telegram: Misha\n"
        "Начать регистрацию: /register 42",
    ]


async def test_hi_after_quit_adds_abandoned_user_to_register_requests_list(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    await dispatcher.feed_update(bot, make_update("/quit"))
    session.clear_messages()

    await dispatcher.feed_update(
        bot,
        make_update(
            "/hi",
            user_id=42,
            first_name="Misha",
            last_name="Petrov",
            username="misha",
        ),
    )
    session.clear_messages()

    await dispatcher.feed_update(
        bot,
        make_update("/register_requests_list", user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == [
        "Заявок на регистрацию нет.\n"
        "\n"
        "Видел незарегистрированных пользователей:\n"
        "1. Misha Petrov (@misha) - Telegram ID 42 - /register 42"
    ]


async def test_non_admin_cannot_register_another_user_by_id(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register 99"))

    assert sent_texts(session) == ["Команда доступна только админам."]
    assert UserRepository(database).get_by_telegram_id(99) is None


async def test_admin_registers_another_user_by_id(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register 42", user_id=7, first_name="Admin"))

    assert sent_texts(session) == [
        "Регистрируем пользователя Telegram ID 42.\n\n"
        "Напиши имя одним сообщением. Например: Максим\n"
        "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду."
    ]
    assert keyboard_texts(session.sent_messages[0]) == [["Telegram ID 42"]]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим", user_id=7, first_name="Admin"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить", user_id=7, first_name="Admin"))
    await dispatcher.feed_update(bot, make_update("Да", user_id=7, first_name="Admin"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да", user_id=7, first_name="Admin"))

    texts = sent_texts(session)
    assert texts[0].startswith("Заявка на регистрацию отправлена. Жду аппрув.")
    assert "Новая регистрация" in texts[1]
    assert "Telegram ID: 42" in texts[1]
    assert "Имя: Максим" in texts[1]
    assert "Аппрув: /approve 42" in texts[1]

    target_user = UserRepository(database).get_by_telegram_id(42)
    admin_user = UserRepository(database).get_by_telegram_id(7)
    assert target_user is not None
    assert target_user.display_name == "Максим"
    assert target_user.status == UserStatus.PENDING
    assert admin_user is None


async def test_admin_registers_seen_user_by_id_with_seen_profile(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)
    TelegramAccountRepository(database).remember(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name="Petrov",
        )
    )

    await dispatcher.feed_update(bot, make_update("/register 42", user_id=7, first_name="Admin"))

    assert sent_texts(session) == [
        "Регистрируем пользователя Telegram ID 42.\n\n"
        "Напиши имя одним сообщением. Например: Максим\n"
        "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду."
    ]
    assert keyboard_texts(session.sent_messages[0]) == [["Misha"]]


async def test_admin_register_target_id_must_be_numeric(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register abc", user_id=7, first_name="Admin"))

    assert sent_texts(session) == ["Telegram ID должен быть числом: /register 123456789"]


async def test_register_flow_creates_pending_user_from_next_message(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))

    assert sent_texts(session) == [
        "Напиши имя одним сообщением. Например: Максим\n"
        "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду."
    ]
    assert keyboard_texts(session.sent_messages[0]) == [["Misha"]]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим"))

    assert sent_texts(session) == [
        "Имя записал: Максим\n\n"
        "Пришли email аккаунта Splitwise, чтобы я проверил тебя в офисной группе.\n"
        "Можно написать «Пропустить»."
    ]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить"))

    assert sent_texts(session) == [
        "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
        "без привязки.\n\n"
        "Звать тебя на ланч упоминанием в общем чате?"
    ]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))

    texts = sent_texts(session)
    assert texts[0] == (
        "Заявка на регистрацию отправлена. Жду аппрув.\n\n"
        "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
        "без привязки.\n\n"
        "Звать на ланч: да.\n"
        "Звать на кофе: да."
    )
    assert "Новая регистрация" in texts[1]
    assert "Splitwise: не указан" in texts[1]

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Максим"
    assert user.status == UserStatus.PENDING


async def test_register_name_button_uses_telegram_first_name_only(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register", last_name="Tarakanov"))

    assert keyboard_texts(session.sent_messages[0]) == [["Misha"]]


async def test_register_flow_keeps_user_in_state_until_valid_name(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("   "))

    assert sent_texts(session) == ["Имя не может быть пустым. Напиши имя, например: Максим"]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим"))

    assert sent_texts(session) == [
        "Имя записал: Максим\n\n"
        "Пришли email аккаунта Splitwise, чтобы я проверил тебя в офисной группе.\n"
        "Можно написать «Пропустить»."
    ]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить"))

    await dispatcher.feed_update(bot, make_update("Да"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))

    assert sent_texts(session)[0].startswith("Заявка на регистрацию отправлена.")
    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Максим"


async def test_register_flow_keeps_user_in_splitwise_step_when_email_not_found(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))
    await dispatcher.feed_update(bot, make_update("Максим"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("missing@example.com"))

    assert sent_texts(session) == [
        "Не нашел такой email в офисной Splitwise-группе.\n"
        "Проверь email и пришли другой или нажми «Пропустить».\n\n"
        "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
        "без привязки."
    ]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить"))

    await dispatcher.feed_update(bot, make_update("Да"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))

    assert sent_texts(session)[0].startswith("Заявка на регистрацию отправлена.")
    assert UserRepository(database).get_by_telegram_id(42) is not None


async def test_register_flow_keeps_user_in_splitwise_step_when_check_is_unavailable(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database, splitwise_unavailable=True)

    await dispatcher.feed_update(bot, make_update("/register"))
    await dispatcher.feed_update(bot, make_update("Максим"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("max@example.com"))

    assert sent_texts(session) == [
        "Не смог проверить Splitwise прямо сейчас.\n"
        "Можно попробовать другой email позже или нажать «Пропустить».\n\n"
        "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
        "без привязки."
    ]
    assert UserRepository(database).get_by_telegram_id(42) is None

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить"))

    await dispatcher.feed_update(bot, make_update("Да"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))

    assert sent_texts(session)[0].startswith("Заявка на регистрацию отправлена.")
    assert UserRepository(database).get_by_telegram_id(42) is not None


async def test_command_interrupts_registration_flow(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/help"))

    assert sent_texts(session) == [PRIVATE_HELP_TEXT]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим"))

    assert sent_texts(session) == []
    assert UserRepository(database).get_by_telegram_id(42) is None


async def test_cancel_interrupts_registration_flow(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/cancel"))

    assert sent_texts(session) == ["Текущий сценарий отменен."]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Максим"))

    assert sent_texts(session) == []
    assert UserRepository(database).get_by_telegram_id(42) is None


async def test_cancel_interrupts_registration_flow_from_splitwise_step(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))
    await dispatcher.feed_update(bot, make_update("Максим"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/cancel"))

    assert sent_texts(session) == ["Текущий сценарий отменен."]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Пропустить"))

    assert sent_texts(session) == []
    assert UserRepository(database).get_by_telegram_id(42) is None


async def test_cancel_without_active_flow_replies_with_noop(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/cancel"))

    assert sent_texts(session) == ["Нет активного сценария."]


async def test_register_notifies_admin_even_when_admin_registers(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(
        dispatcher,
        bot,
        session,
        user_id=7,
        first_name="Admin",
        username="admin",
    )

    assert sent_texts(session)[0].startswith("Заявка на регистрацию отправлена.")
    assert "Новая регистрация" in sent_texts(session)[1]
    assert "Имя: Максим" in sent_texts(session)[1]
    assert "Аппрув: /approve 7" in sent_texts(session)[1]


async def test_register_updates_existing_pending_request(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database, splitwise_members=(make_splitwise_member(),))

    await submit_registration(
        dispatcher,
        bot,
        session,
        splitwise_answer="max@example.com",
    )
    session.clear_messages()
    await submit_registration(dispatcher, bot, session, display_name="Другое")

    texts = sent_texts(session)
    assert texts[0].startswith("Заявка обновлена. Жду аппрув.")
    assert "Обновленная регистрация" in texts[1]
    assert "Telegram ID: 42" in texts[1]
    assert "Имя:\nБыло: Максим\nСтало: Другое" in texts[1]
    assert (
        "Splitwise:\n"
        "Было: max@example.com (ID 1001)\n"
        "Стало: не указан"
    ) in texts[1]

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Другое"

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/register_requests_list", user_id=7))

    assert sent_texts(session) == [
        "Заявки на регистрацию:\n"
        "1. Другое (@misha) - Telegram ID 42 - Splitwise: не указан - /approve 42"
    ]


async def test_register_existing_pending_request_with_same_data_is_noop(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()

    await submit_registration(dispatcher, bot, session)

    assert sent_texts(session) == ["Заявка уже ждет аппрува, Максим"]


async def test_register_existing_active_user_asks_for_reregistration_confirmation(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await submit_registration(dispatcher, bot, session, display_name="Другое")

    assert sent_texts(session) == [
        "Вы уже зарегистрированы.\n"
        "Текущие данные:\n"
        "Имя: Максим\n"
        "Telegram ID: 42\n"
        "Username: @misha\n"
        "Splitwise: не указан\n"
        "\n"
        "Новые данные:\n"
        "Имя: Другое\n"
        "Splitwise: не указан\n"
        "\n"
        "Перерегистрировать вас?"
    ]
    reply_markup = session.sent_messages[0].reply_markup
    assert reply_markup is not None
    assert [
        [button.text for button in row]
        for row in reply_markup.keyboard
    ] == [["Да", "Нет"]]


async def test_register_existing_active_user_with_same_data_does_not_reregister(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await submit_registration(dispatcher, bot, session)

    assert sent_texts(session) == ["Ваши данные не изменились. Перерегистрацию не запускаю."]
    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.status == UserStatus.ACTIVE


async def test_register_existing_active_user_can_confirm_reregistration(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await submit_registration(dispatcher, bot, session, display_name="Другое")
    session.clear_messages()
    await dispatcher.feed_update(
        bot,
        make_update("Да", username="new_username", first_name="New", last_name="Name"),
    )

    texts = sent_texts(session)
    assert texts[0] == (
        "Заявка на перерегистрацию отправлена. Жду аппрув.\n\n"
        "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
        "без привязки."
    )
    assert "Перерегистрация" in texts[1]
    assert "Имя:\nБыло: Максим\nСтало: Другое" in texts[1]
    assert "Аппрув: /approve 42" in texts[1]
    assert session.sent_messages[0].reply_markup is not None
    assert session.sent_messages[0].reply_markup.remove_keyboard is True

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Другое"
    assert user.status == UserStatus.PENDING
    assert user.username == "new_username"
    assert user.first_name == "New"
    assert user.last_name == "Name"

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/register_requests_list", user_id=7))

    assert sent_texts(session) == [
        "Заявки на регистрацию:\n"
        "1. Другое (@new_username) - Telegram ID 42 - Splitwise: не указан - /approve 42"
    ]


async def test_register_existing_active_user_can_decline_reregistration(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await submit_registration(dispatcher, bot, session, display_name="Другое")
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Нет"))

    assert sent_texts(session) == ["Оставил текущую регистрацию."]
    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Максим"


async def test_admin_can_approve_pending_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))

    assert sent_texts(session) == [
        "Аппрувнул: Максим",
        "Регистрация подтверждена. Теперь я буду звать тебя Максим.",
    ]

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.status == UserStatus.ACTIVE


async def test_non_admin_cannot_approve(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=99, first_name="NotAdmin"))

    assert sent_texts(session) == ["Команда доступна только админам."]


async def test_admin_can_list_pending_registration_requests(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await submit_registration(
        dispatcher,
        bot,
        session,
        user_id=43,
        first_name="Olya",
        username="olya",
        display_name="Оля",
    )
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/register_requests_list", user_id=7))

    assert sent_texts(session) == [
        "Заявки на регистрацию:\n"
        "1. Максим (@misha) - Telegram ID 42 - Splitwise: не указан - /approve 42\n"
        "2. Оля (@olya) - Telegram ID 43 - Splitwise: не указан - /approve 43"
    ]


async def test_non_admin_cannot_list_pending_registration_requests(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register_requests_list", user_id=99))

    assert sent_texts(session) == ["Команда доступна только админам."]


async def test_admin_sees_empty_registration_request_list(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register_requests_list", user_id=7))

    assert sent_texts(session) == ["Заявок на регистрацию нет."]


async def test_meta_uses_registered_display_name(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/meta 25", chat_type="group"))

    assert sent_texts(session) == ["Максим будет в 12:40"]


async def test_meta_reports_arrival_time_range(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/meta 20-30", chat_type="group"))

    assert sent_texts(session) == ["Максим будет с 12:35 до 12:45"]


async def test_eta_reports_delivery_arrival_time(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/eta 20", chat_type="group"))

    assert sent_texts(session) == ["Ожидаемое время прибытия доставки 12:35"]


async def test_eta_reports_delivery_arrival_time_range(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/eta 20-30", chat_type="group"))

    assert sent_texts(session) == ["Ожидаемое время прибытия доставки с 12:35 до 12:45"]


async def test_eta_requires_minutes_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/eta", chat_type="group"))

    assert sent_texts(session) == [
        "Напиши через сколько минут или диапазон: /eta 20 или /eta 20-30"
    ]


async def test_eta_rejects_invalid_minutes_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/eta abc", chat_type="group"))

    assert sent_texts(session) == [
        "Минуты должны быть числом или диапазоном: /eta 20 или /eta 20-30"
    ]


async def test_eta_rejects_too_large_minutes_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/eta 9999999999", chat_type="group"))

    assert sent_texts(session) == [
        "Минуты должны быть от 0 до 527040 (366 дней): /eta 20 или /eta 20-30"
    ]


async def test_eta_rejects_negative_minutes_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/eta -1", chat_type="group"))

    assert sent_texts(session) == [
        "Минуты должны быть от 0 до 527040 (366 дней): /eta 20 или /eta 20-30"
    ]


async def test_meta_requires_minutes_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/meta", chat_type="group"))

    assert sent_texts(session) == [
        "Напиши через сколько минут или диапазон: /meta 25 или /meta 20-30"
    ]


async def test_meta_rejects_invalid_minutes_range(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/meta 30-20", chat_type="group"))

    assert sent_texts(session) == ["Начало диапазона должно быть не больше конца: /meta 20-30"]


async def test_registration_happy_path_allows_meta_after_approval(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    assert sent_texts(session)[0].startswith("Заявка на регистрацию отправлена. Жду аппрув.")
    assert "Аппрув: /approve 42" in sent_texts(session)[1]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    assert sent_texts(session) == [
        "Аппрувнул: Максим",
        "Регистрация подтверждена. Теперь я буду звать тебя Максим.",
    ]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/meta 25", chat_type="group"))
    assert sent_texts(session) == ["Максим будет в 12:40"]


async def test_meta_requires_approved_registration(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/meta 25", chat_type="group"))

    assert sent_texts(session) == ["Регистрация еще ждет аппрува."]


async def test_balance_requires_active_user_and_has_placeholder(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/balance"))

    assert sent_texts(session) == ["Splitwise пока не подключен."]


async def test_balance_works_in_group_chat(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/balance", chat_type="group"))

    assert sent_texts(session) == ["Splitwise пока не подключен."]


async def test_balance_returns_splitwise_balances_for_active_linked_users(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        splitwise_members=(
            make_splitwise_member(email="max@example.com", balance_amount="277.97"),
            make_splitwise_member(
                splitwise_user_id=1002,
                email="anton@example.com",
                balance_amount="-10837.88",
            ),
            make_splitwise_member(
                splitwise_user_id=1003,
                email="tim@example.com",
                balance_amount="18976.74",
            ),
        ),
    )

    await submit_registration(
        dispatcher,
        bot,
        session,
        display_name="Максим",
        splitwise_answer="max@example.com",
    )
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    await submit_registration(
        dispatcher,
        bot,
        session,
        user_id=43,
        first_name="Anton",
        username="anton",
        display_name="Антон",
        splitwise_answer="anton@example.com",
    )
    await dispatcher.feed_update(bot, make_update("/approve 43", user_id=7, first_name="Admin"))
    await submit_registration(
        dispatcher,
        bot,
        session,
        user_id=44,
        first_name="Tim",
        username="tim",
        display_name="Тимофей",
        splitwise_answer="tim@example.com",
    )
    await dispatcher.feed_update(bot, make_update("/approve 44", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/balance"))

    assert sent_texts(session) == [
        "<b>Балансы Splitwise</b>\n"
        "\n"
        '🔴 <b>−10 837.88 RSD</b> · '
        '<a href="https://t.me/anton">Антон</a>\n'
        '⚪    +277.97 RSD · '
        '<a href="https://t.me/misha">Максим</a>\n'
        '🟢 +18 976.74 RSD · '
        '<a href="https://t.me/tim">Тимофей</a>'
    ]
    assert session.sent_messages[0].parse_mode == ParseMode.HTML
    link_preview_options = session.sent_messages[0].link_preview_options
    assert link_preview_options is not None
    assert link_preview_options.is_disabled is True


async def test_vacation_sets_shows_and_clears_status_for_active_user(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/vacation 1", chat_type="group"))
    await dispatcher.feed_update(bot, make_update("/vacation", chat_type="group"))
    await dispatcher.feed_update(bot, make_update("/vacation 0", chat_type="group"))
    await dispatcher.feed_update(bot, make_update("/vacation", chat_type="group"))

    assert sent_texts(session) == [
        "Максим в отпуске до 30.06.2026. Чтобы выйти из отпуска: /vacation 0",
        "Максим в отпуске до 30.06.2026.\n\n"
        "Уйти в отпуск или изменить дату: /vacation 2 или /vacation 20.07\n"
        "Выйти из отпуска: /vacation 0 или /vacation off",
        "Максим больше не в отпуске.",
        "Максим не в отпуске.\n\n"
        "Уйти в отпуск или изменить дату: /vacation 2 или /vacation 20.07\n"
        "Выйти из отпуска: /vacation 0 или /vacation off",
    ]


async def test_vacation_rejects_invalid_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/vacation nope", chat_type="group"))

    assert sent_texts(session) == [
        "Не понял дату. Напиши количество дней или дату: "
        "/vacation 2, /vacation 20.07, /vacation 2026-07-20"
    ]


async def test_lunch_requires_registered_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert sent_texts(session) == ["Сначала зарегистрируйся: /register"]
    assert session.sent_polls == []


async def test_lunch_requires_active_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert sent_texts(session) == ["Регистрация еще ждет аппрува."]
    assert session.sent_polls == []


async def test_lunch_creates_non_anonymous_polls_for_active_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(
            2026,
            7,
            6,
            12,
            15,
            tzinfo=ZoneInfo("Europe/Belgrade"),
        ),
    )
    pins = LunchPinRepository(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    old_pin = pins.upsert(-100, 99, date(2026, 7, 8))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert sent_texts(session) == ["Время обедать! @misha"]
    assert len(session.sent_polls) == 2

    lunch_poll = session.sent_polls[0]
    assert lunch_poll.question == SKYLINE_LUNCH_POLLS.lunch.question
    assert poll_option_texts(lunch_poll) == [
        option.display_value for option in SKYLINE_LUNCH_POLLS.lunch.options
    ]
    assert lunch_poll.is_anonymous is False
    assert lunch_poll.allows_multiple_answers is False
    assert lunch_poll.allow_adding_options is True

    place_poll = session.sent_polls[1]
    assert place_poll.question == SKYLINE_LUNCH_POLLS.place.question
    assert poll_option_texts(place_poll) == [
        option.display_value for option in SKYLINE_LUNCH_POLLS.place.options
    ]
    assert place_poll.is_anonymous is False
    assert place_poll.allows_multiple_answers is True
    assert place_poll.allow_adding_options is True
    assert session.pin_requests == []
    assert session.unpin_requests == []
    assert pins.get(-100) == old_pin


async def test_lunch_uses_rose_poll_definitions_on_tuesday(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(
            2026,
            7,
            7,
            12,
            15,
            tzinfo=ZoneInfo("Europe/Belgrade"),
        ),
    )

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert len(session.sent_polls) == 2
    assert poll_option_texts(session.sent_polls[0]) == [
        option.display_value for option in ROSE_LUNCH_POLLS.lunch.options
    ]
    assert poll_option_texts(session.sent_polls[1]) == [
        option.display_value for option in ROSE_LUNCH_POLLS.place.options
    ]


@pytest.mark.parametrize(
    ("command_text", "day", "expected_polls"),
    [
        ("/lunch rose", 6, ROSE_LUNCH_POLLS),
        ("/lunch роза", 6, ROSE_LUNCH_POLLS),
        ("/lunch skyline", 7, SKYLINE_LUNCH_POLLS),
        ("/lunch скайлайн", 7, SKYLINE_LUNCH_POLLS),
    ],
)
async def test_lunch_office_argument_overrides_weekday(
    tmp_path: Path,
    command_text: str,
    day: int,
    expected_polls: OfficeLunchPolls,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(
            2026,
            7,
            day,
            12,
            15,
            tzinfo=ZoneInfo("Europe/Belgrade"),
        ),
    )

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update(command_text, chat_type="group"))

    assert len(session.sent_polls) == 2
    assert poll_option_texts(session.sent_polls[0]) == [
        option.display_value for option in expected_polls.lunch.options
    ]
    assert poll_option_texts(session.sent_polls[1]) == [
        option.display_value for option in expected_polls.place.options
    ]


async def test_lunch_rejects_unknown_office_argument(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch office", chat_type="group"))

    assert sent_texts(session) == [
        "Не понял офис. Используй /lunch, /lunch rose, /lunch роза, "
        "/lunch skyline или /lunch скайлайн."
    ]
    assert session.sent_polls == []


async def test_lunch_skips_vacation_users_in_announcement(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)
    users = UserRepository(database)
    vacations = VacationRepository(database)
    max_user = users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)
    users.create_pending_user(
        TelegramProfile(
            telegram_user_id=43,
            username="olya",
            first_name="Olya",
            last_name=None,
        ),
        "Оля",
    )
    users.approve_by_telegram_id(43)
    vacations.set_until_date(max_user.id, date(2026, 6, 30))

    await dispatcher.feed_update(
        bot,
        make_update("/lunch", user_id=43, username="olya", chat_type="group"),
    )

    assert sent_texts(session) == ["Время обедать! @olya"]
    assert len(session.sent_polls) == 2


async def test_manual_lunch_publishes_without_tags_when_all_active_users_are_on_vacation(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/vacation 1", chat_type="group"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert sent_texts(session) == ["Время обедать!"]
    assert len(session.sent_polls) == 2


async def test_lunch_tags_user_after_vacation_expires(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(2026, 7, 1, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )
    users = UserRepository(database)
    user = users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)
    VacationRepository(database).set_until_date(user.id, date(2026, 6, 30))

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))

    assert sent_texts(session) == ["Время обедать! @misha"]
    assert len(session.sent_polls) == 2


async def test_lunch_auto_commands_manage_current_group_chat(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/lunch_auto_on",
            user_id=7,
            first_name="Admin",
            chat_type="group",
            chat_id=-100,
            chat_title="Office",
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_update(
            "/lunch_auto_status",
            user_id=7,
            first_name="Admin",
            chat_type="group",
            chat_id=-100,
            chat_title="Office",
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_update(
            "/lunch_auto_off",
            user_id=7,
            first_name="Admin",
            chat_type="group",
            chat_id=-100,
            chat_title="Office",
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_update(
            "/lunch_auto_status",
            user_id=7,
            first_name="Admin",
            chat_type="group",
            chat_id=-100,
            chat_title="Office",
        ),
    )

    assert sent_texts(session) == [
        "Авто-ланч включен для этого чата.",
        "Авто-ланч включен для этого чата.",
        "Авто-ланч выключен для этого чата.",
        "Авто-ланч выключен для этого чата.",
    ]
    chat = LunchAutoChatRepository(database).get(-100)
    assert chat is not None
    assert chat.title == "Office"
    assert not chat.enabled


async def test_lunch_auto_command_addressed_to_this_bot_works_in_group(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(
            "/lunch_auto_on@foodbot_dev",
            user_id=7,
            first_name="Admin",
            chat_type="group",
            chat_id=-100,
            chat_title="Office",
        ),
    )

    assert sent_texts(session) == ["Авто-ланч включен для этого чата."]
    chat = LunchAutoChatRepository(database).get(-100)
    assert chat is not None
    assert chat.enabled


async def test_lunch_auto_commands_are_admin_only(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/lunch_auto_on", chat_type="group"))

    assert sent_texts(session) == ["Команда доступна только админам."]
    assert LunchAutoChatRepository(database).get(-100) is None


async def test_scheduled_lunch_uses_rose_polls_and_tracks_actions_on_tuesday(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(
        database,
        clock=lambda: datetime(
            2026,
            7,
            7,
            11,
            30,
            tzinfo=ZoneInfo("Europe/Belgrade"),
        ),
    )
    services.lunch_auto_chats.enable(-100, "Office")
    users = UserRepository(database)
    users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)

    await services.lunch_scheduler.run_due_lunch(bot)

    assert sent_texts(session) == ["Время обедать! @misha"]
    assert len(session.sent_polls) == 2
    assert session.sent_polls[0].chat_id == -100
    assert poll_option_texts(session.sent_polls[0]) == [
        option.display_value for option in ROSE_LUNCH_POLLS.lunch.options
    ]
    assert poll_option_texts(session.sent_polls[1]) == [
        option.display_value for option in ROSE_LUNCH_POLLS.place.options
    ]
    assert session.unpin_requests == []
    assert len(session.pin_requests) == 1
    assert session.pin_requests[0].chat_id == -100
    assert session.pin_requests[0].message_id == 2
    assert session.pin_requests[0].disable_notification is True
    action_requests = services.poll_tracking.consume_action_requests(
        session.sent_poll_ids[1],
        42,
        (ROSE_OTHER_OPTION_INDEX,),
    )
    assert len(action_requests) == 1
    assert action_requests[0].chat_id == -100


async def test_scheduled_lunch_replaces_previous_pinned_poll(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    services.lunch_auto_chats.enable(-100, "Office")
    users = UserRepository(database)
    users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)

    await services.lunch_scheduler.run_due_lunch(bot)
    await services.lunch_scheduler.run_due_lunch(bot)

    assert [request.message_id for request in session.pin_requests] == [2, 5]
    assert [request.message_id for request in session.unpin_requests] == [2]
    current_pin = LunchPinRepository(database).get(-100)
    assert current_pin is not None
    assert current_pin.message_id == 5


async def test_scheduled_lunch_still_publishes_when_pin_fails(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession(failed_method_names=frozenset({"PinChatMessage"}))
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    services.lunch_auto_chats.enable(-100, "Office")
    users = UserRepository(database)
    users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)

    await services.lunch_scheduler.run_due_lunch(bot)

    assert sent_texts(session) == ["Время обедать! @misha"]
    assert len(session.sent_polls) == 2
    assert LunchPinRepository(database).get(-100) is None


async def test_scheduled_lunch_clears_previous_pin_when_publish_fails(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession(failed_method_names=frozenset({"SendMessage"}))
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    services.lunch_auto_chats.enable(-100, "Office")
    LunchPinRepository(database).upsert(-100, 10, date(2026, 6, 29))

    await services.lunch_scheduler.run_due_lunch(bot)

    assert sent_texts(session) == []
    assert session.sent_polls == []
    assert session.pin_requests == []
    assert [request.message_id for request in session.unpin_requests] == [10]
    assert LunchPinRepository(database).get(-100) is None


async def test_scheduled_lunch_skips_when_all_active_users_are_on_vacation(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    services.lunch_auto_chats.enable(-100, "Office")
    users = UserRepository(database)
    user = users.create_pending_user(
        TelegramProfile(
            telegram_user_id=42,
            username="misha",
            first_name="Misha",
            last_name=None,
        ),
        "Максим",
    )
    users.approve_by_telegram_id(42)
    VacationRepository(database).set_until_date(user.id, date(2026, 6, 30))
    LunchPinRepository(database).upsert(-100, 10, date(2026, 6, 29))

    await services.lunch_scheduler.run_due_lunch(bot)

    assert sent_texts(session) == []
    assert session.sent_polls == []
    assert session.pin_requests == []
    assert [request.message_id for request in session.unpin_requests] == [10]
    assert LunchPinRepository(database).get(-100) is None


async def test_scheduled_lunch_skips_serbian_holiday(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(
        database,
        clock=lambda: datetime(2026, 1, 1, 11, 30, tzinfo=ZoneInfo("Europe/Belgrade")),
    )
    services.lunch_auto_chats.enable(-100, "Office")
    LunchPinRepository(database).upsert(-100, 10, date(2025, 12, 31))

    await services.lunch_scheduler.run_due_lunch(bot)

    assert session.sent_polls == []
    assert [request.message_id for request in session.unpin_requests] == [10]
    assert LunchPinRepository(database).get(-100) is None


async def test_scheduled_lunch_skips_weekend(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(
        database,
        clock=lambda: datetime(2026, 7, 4, 11, 30, tzinfo=ZoneInfo("Europe/Belgrade")),
    )
    services.lunch_auto_chats.enable(-100, "Office")
    LunchPinRepository(database).upsert(-100, 10, date(2026, 7, 3))

    await services.lunch_scheduler.run_due_lunch(bot)

    assert session.sent_polls == []
    assert [request.message_id for request in session.unpin_requests] == [10]
    assert LunchPinRepository(database).get(-100) is None


async def test_admin_debug_allows_group_only_command_in_private_chat(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(
        dispatcher,
        bot,
        session,
        user_id=7,
        first_name="Admin",
        username="admin",
    )
    await dispatcher.feed_update(bot, make_update("/approve 7", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(
        bot,
        make_update("/lunch rose", user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == ["Команда доступна только в групповом чате."]
    assert session.sent_polls == []

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/debug 1", user_id=7, first_name="Admin"))

    assert sent_texts(session) == ["Debug включен. В личке доступны все команды."]
    assert len(session.set_command_requests) == 1
    assert _command_names(tuple(session.set_command_requests[0].commands)) == [
        definition.name for definition in COMMANDS if definition.show_in_menu
    ]

    session.clear_messages()
    await dispatcher.feed_update(
        bot,
        make_update("/lunch rose", user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == ["Время обедать! @admin"]
    assert len(session.sent_polls) == 2

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/debug 0", user_id=7, first_name="Admin"))

    assert sent_texts(session) == ["Debug выключен."]
    assert len(session.set_command_requests) == 2

    session.clear_messages()
    await dispatcher.feed_update(
        bot,
        make_update("/lunch rose", user_id=7, first_name="Admin"),
    )

    assert sent_texts(session) == ["Команда доступна только в групповом чате."]
    assert session.sent_polls == []


async def test_rose_lunch_other_place_answer_creates_other_food_poll_once(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(
            2026,
            7,
            7,
            12,
            15,
            tzinfo=ZoneInfo("Europe/Belgrade"),
        ),
    )

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    place_poll_id = session.sent_poll_ids[1]
    session.clear_messages()

    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(
            place_poll_id,
            (0, ROSE_OTHER_OPTION_INDEX),
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(
            place_poll_id,
            (ROSE_OTHER_OPTION_INDEX,),
            user_id=43,
            first_name="Anton",
            username="anton",
        ),
    )

    assert sent_texts(session) == []
    assert len(session.sent_polls) == 1
    other_food_poll = session.sent_polls[0]
    assert other_food_poll.question == LUNCH_OTHER_FOOD_POLL.question
    assert poll_option_texts(other_food_poll) == [
        option.display_value for option in LUNCH_OTHER_FOOD_POLL.options
    ]
    assert other_food_poll.is_anonymous is False
    assert other_food_poll.allows_multiple_answers is True
    assert other_food_poll.allow_adding_options is True
    stored_kinds = {
        str(row["kind"])
        for row in database.connection.execute("SELECT kind FROM polls").fetchall()
    }
    assert stored_kinds == {
        PollKind.LUNCH_ATTENDANCE_V1.value,
        PollKind.LUNCH_PLACE_ROSE_V1.value,
        PollKind.LUNCH_OTHER_FOOD_V1.value,
    }


async def test_lunch_place_answer_without_other_choice_does_not_create_poll(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(
            2026,
            7,
            7,
            12,
            15,
            tzinfo=ZoneInfo("Europe/Belgrade"),
        ),
    )

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    place_poll_id = session.sent_poll_ids[1]
    session.clear_messages()

    await dispatcher.feed_update(bot, make_poll_answer_update(place_poll_id, (0, 1)))

    assert sent_texts(session) == []
    assert session.sent_polls == []


async def test_lunch_poll_action_survives_service_restart(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    first_dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(2026, 7, 7, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )
    await first_dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    place_poll_id = session.sent_poll_ids[1]
    session.clear_messages()
    restarted_dispatcher = make_dispatcher(
        database,
        clock=lambda: datetime(2026, 7, 7, 12, 16, tzinfo=ZoneInfo("Europe/Belgrade")),
    )

    await restarted_dispatcher.feed_update(
        bot,
        make_poll_answer_update(place_poll_id, (ROSE_OTHER_OPTION_INDEX,)),
    )

    assert len(session.sent_polls) == 1
    assert session.sent_polls[0].question == LUNCH_OTHER_FOOD_POLL.question


async def test_coffee_without_arguments_shows_status_usage_and_meeting(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/coffee", chat_type="group"))

    assert sent_texts(session) == [
        "Приглашения на кофе: включены.\n\n"
        "Создать или перенести встречу: /coffee 15 или /coffee 16:30.\n\n"
        "Текущей встречи нет."
    ]


@pytest.mark.parametrize("alias", ["/кофе", "/КоФе", "/КОФЕ@foodbot_dev"])
async def test_russian_coffee_alias_without_arguments_shows_status(
    alias: str,
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update(alias, chat_type="group"))

    assert sent_texts(session) == [
        "Приглашения на кофе: включены.\n\n"
        "Создать или перенести встречу: /coffee 15 или /coffee 16:30.\n\n"
        "Текущей встречи нет."
    ]


async def test_russian_coffee_alias_updates_invitation_preference(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/кофе off", chat_type="group"))
    await dispatcher.feed_update(bot, make_update("/кофе on", chat_type="group"))
    await dispatcher.feed_update(bot, make_update("/кофе", chat_type="group"))

    assert sent_texts(session) == [
        "Приглашения на кофе выключены.",
        "Приглашения на кофе включены.",
        "Приглашения на кофе: включены.\n\n"
        "Создать или перенести встречу: /coffee 15 или /coffee 16:30.\n\n"
        "Текущей встречи нет.",
    ]


async def test_russian_coffee_alias_obeys_group_scope(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/кофе 15"))

    assert sent_texts(session) == ["Команда доступна только в групповом чате."]
    assert CoffeeSessionRepository(database).get_open_for_chat(42) is None


async def test_russian_coffee_alias_works_in_admin_private_debug(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 7, "Админ", "admin")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    services.debug.set_enabled(7, True)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(
        bot,
        make_update("/кофе 15", user_id=7, username="admin"),
    )

    assert CoffeeSessionRepository(database).get_open_for_chat(7) is not None
    assert sent_texts(session)[0].startswith("☕ Админ предлагает кофе")


async def test_russian_coffee_alias_for_another_bot_is_ignored(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update("/кофе@another_bot 15", chat_type="group"),
    )

    assert sent_texts(session) == []
    assert CoffeeSessionRepository(database).get_open_for_chat(-100) is None


async def test_coffee_off_changes_only_invitation_preference(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/coffee off", chat_type="group"))
    await dispatcher.feed_update(bot, make_update("/coffee", chat_type="group"))

    assert sent_texts(session) == [
        "Приглашения на кофе выключены.",
        "Приглашения на кофе: выключены.\n\n"
        "Создать или перенести встречу: /coffee 15 или /coffee 16:30.\n\n"
        "Текущей встречи нет.",
    ]


async def test_coffee_creates_card_and_persists_session(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))

    assert sent_texts(session) == [
        "☕ Максим предлагает кофе\n"
        "Время: <b>12:30</b>\n"
        "Через: <b>15 минут</b>\n\n"
        "Идут (1):\n• Максим"
    ]
    assert session.sent_messages[0].parse_mode == ParseMode.HTML
    assert inline_callback_data(session.sent_messages[0]).keys() == {
        "Пойду",
        "Не пойду",
    }
    assert len(session.pin_requests) == 1
    assert session.pin_requests[0].message_id == 1
    assert session.pin_requests[0].disable_notification is True
    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    assert coffee_session.message_id == 1
    assert [user.display_name for user in CoffeeSessionRepository(database).list_participants(
        coffee_session.id
    )] == ["Максим"]


@pytest.mark.parametrize(
    ("minutes", "countdown_is_visible"),
    [(59, True), (60, False), (61, False)],
)
async def test_coffee_card_shows_countdown_only_during_last_hour(
    tmp_path: Path,
    minutes: int,
    countdown_is_visible: bool,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(
        bot,
        make_update(f"/coffee {minutes}", chat_type="group"),
    )

    assert ("Через:" in sent_texts(session)[0]) is countdown_is_visible


@pytest.mark.parametrize(
    ("alias", "expected_time"),
    [("/кофе 15", "12:30"), ("/кофе 16:30", "16:30")],
)
async def test_russian_coffee_alias_creates_session(
    alias: str,
    expected_time: str,
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update(alias, chat_type="group"))

    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    assert coffee_session.message_id == 1
    assert f"Время: <b>{expected_time}</b>" in sent_texts(session)[0]


async def test_coffee_countdown_edits_existing_card_without_new_message(
    tmp_path: Path,
) -> None:
    now = [datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade"))]
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database, clock=lambda: now[0])

    await services.coffee.create_or_reschedule(bot, -100, 42, "15")
    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    session.clear_messages()
    now[0] = datetime(2026, 6, 30, 12, 16, tzinfo=ZoneInfo("Europe/Belgrade"))

    await services.coffee.refresh_countdown(bot, coffee_session.id)

    assert session.sent_messages == []
    assert len(session.edited_messages) == 1
    assert session.edited_messages[0].message_id == coffee_session.message_id
    assert session.edited_messages[0].text == (
        "☕ Максим предлагает кофе\n"
        "Время: <b>12:30</b>\n"
        "Через: <b>14 минут</b>\n\n"
        "Идут (1):\n• Максим"
    )
    assert session.pin_requests == []


async def test_coffee_reschedule_edits_card_and_keeps_participants(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    activate_user(database, 43, "Анна", "anna")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))
    await dispatcher.feed_update(
        bot,
        make_update(
            "/coffee 30",
            user_id=43,
            first_name="Anna",
            username="anna",
            chat_type="group",
        ),
    )

    assert len(session.sent_messages) == 2
    assert session.sent_messages[1].text == (
        "Анна предлагает новое время кофе: 12:45."
    )
    assert session.sent_messages[1].reply_parameters is not None
    assert session.sent_messages[1].reply_parameters.message_id == 1
    assert len(session.edited_messages) == 1
    assert session.edited_messages[0].text == (
        "☕ Анна предлагает кофе\n"
        "Время: <b>12:45</b>\n"
        "Через: <b>30 минут</b>\n\n"
        "Идут (2):\n• Максим\n• Анна"
    )
    assert session.edited_messages[0].parse_mode == ParseMode.HTML
    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    assert [user.display_name for user in CoffeeSessionRepository(database).list_participants(
        coffee_session.id
    )] == ["Максим", "Анна"]
    assert len(session.pin_requests) == 1


async def test_concurrent_coffee_reschedules_are_serialized(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    await services.coffee.create_or_reschedule(bot, -100, 42, "15")

    await asyncio.gather(
        services.coffee.create_or_reschedule(bot, -100, 42, "20"),
        services.coffee.create_or_reschedule(bot, -100, 42, "30"),
    )

    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    local_time = coffee_session.scheduled_at.astimezone(
        ZoneInfo("Europe/Belgrade")
    ).strftime("%H:%M")
    assert local_time == "12:45"


async def test_failed_coffee_card_update_rolls_back_reschedule(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    activate_user(database, 43, "Анна", "anna")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    await services.coffee.create_or_reschedule(bot, -100, 42, "15")
    session.fail_methods("EditMessageText", "SendMessage")

    with pytest.raises(TelegramBadRequest):
        await services.coffee.create_or_reschedule(bot, -100, 43, "30")

    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    local_time = coffee_session.scheduled_at.astimezone(
        ZoneInfo("Europe/Belgrade")
    ).strftime("%H:%M")
    assert local_time == "12:30"
    assert [
        user.display_name
        for user in CoffeeSessionRepository(database).list_participants(
            coffee_session.id
        )
    ] == ["Максим"]


async def test_coffee_shout_combines_persisted_lunch_poll_answers(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    activate_user(database, 43, "Анна", "anna")
    activate_user(database, 44, "Борис", "boris")
    activate_user(database, 45, "Вера", "vera")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    attendance_poll_id = session.sent_poll_ids[0]
    place_poll_id = session.sent_poll_ids[1]
    independent_option_index = ROSE_LUNCH_POLLS.lunch.options.index(
        PollOption.LUNCH_EAT_INDEPENDENTLY
    )
    place_option_index = ROSE_LUNCH_POLLS.place.options.index(
        PollOption.LUNCH_PLACE_ROSE_BEREZKA
    )
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(
            attendance_poll_id,
            (independent_option_index,),
            user_id=43,
            username="anna",
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(
            place_poll_id,
            (place_option_index,),
            user_id=44,
            username="boris",
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(
            attendance_poll_id,
            (independent_option_index,),
            user_id=45,
            username="vera",
        ),
    )
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(
            place_poll_id,
            (place_option_index,),
            user_id=45,
            username="vera",
        ),
    )
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))

    assert len(session.sent_messages) == 2
    assert (
        session.sent_messages[0].text
        == "@anna @boris @vera, присоединяйтесь на кофе."
    )
    assert session.sent_messages[0].reply_parameters is None
    assert session.sent_messages[1].text == (
        "☕ Максим предлагает кофе\n"
        "Время: <b>12:30</b>\n"
        "Через: <b>15 минут</b>\n\n"
        "Идут (1):\n• Максим"
    )
    assert session.pin_requests[0].message_id == 2


async def test_coffee_card_is_created_when_shout_fails(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    activate_user(database, 43, "Анна", "anna")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    attendance_poll_id = session.sent_poll_ids[0]
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(attendance_poll_id, (1,), user_id=43, username="anna"),
    )
    session.clear_messages()
    session.fail_next_send_message()

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))

    assert sent_texts(session) == [
        "☕ Максим предлагает кофе\n"
        "Время: <b>12:30</b>\n"
        "Через: <b>15 минут</b>\n\n"
        "Идут (1):\n• Максим"
    ]
    assert session.pin_requests[0].message_id == 1


async def test_coffee_leave_button_makes_empty_session_complete_silently(
    tmp_path: Path,
) -> None:
    now = [datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade"))]
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database, clock=lambda: now[0])
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))
    callback_data = inline_callback_data(session.sent_messages[0])["Не пойду"]
    await dispatcher.feed_update(bot, make_callback_update(callback_data))
    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    session.clear_messages()
    now[0] = datetime(2026, 6, 30, 12, 30, tzinfo=ZoneInfo("Europe/Belgrade"))

    await services.coffee.complete(bot, coffee_session.id)

    assert sent_texts(session) == []
    assert len(session.unpin_requests) == 1
    assert session.unpin_requests[0].message_id == coffee_session.message_id
    completed = CoffeeSessionRepository(database).require(coffee_session.id)
    assert completed.status == CoffeeSessionStatus.COMPLETED


async def test_coffee_callback_rejects_unregistered_user_with_alert(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)
    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))
    callback_data = inline_callback_data(session.sent_messages[0])["Пойду"]

    await dispatcher.feed_update(
        bot,
        make_callback_update(callback_data, user_id=99, username="unknown"),
    )

    assert session.callback_answers[-1].show_alert is True
    assert session.callback_answers[-1].text == (
        "Чтобы пользоваться этой функцией, сначала зарегистрируйся.\n"
        "В личном чате с ботом запусти /register и пройди регистрацию сам "
        "или отправь /request_register, чтобы тебя зарегистрировал администратор."
    )


async def test_repeated_coffee_join_is_idempotent_and_does_not_edit_card(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)
    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))
    callback_data = inline_callback_data(session.sent_messages[0])["Пойду"]
    session.clear_messages()

    await dispatcher.feed_update(bot, make_callback_update(callback_data))

    assert session.sent_messages == []
    assert session.edited_messages == []
    assert session.callback_answers[-1].text is None


async def test_coffee_completion_exhausts_retries_and_marks_failed(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))
    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    session.fail_methods("SendMessage")

    for _ in range(4):
        await services.coffee.complete(bot, coffee_session.id)

    failed = CoffeeSessionRepository(database).require(coffee_session.id)
    assert failed.status == CoffeeSessionStatus.FAILED
    assert failed.notification_attempts == 3


async def test_coffee_completion_unpins_card_and_calls_participants(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    await services.coffee.create_or_reschedule(bot, -100, 42, "15")
    coffee_session = CoffeeSessionRepository(database).get_open_for_chat(-100)
    assert coffee_session is not None
    session.clear_messages()

    await services.coffee.complete(bot, coffee_session.id)

    assert len(session.unpin_requests) == 1
    assert session.unpin_requests[0].message_id == coffee_session.message_id
    assert len(session.edited_messages) == 1
    assert "Встреча прошла" in session.edited_messages[0].text
    assert "Через:" not in session.edited_messages[0].text
    assert session.edited_messages[0].reply_markup is None
    assert sent_texts(session) == ["☕ Пора идти за кофе!\n@misha"]


async def test_coffee_recovery_expires_session_older_than_grace_period(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    users = UserRepository(database)
    user = users.get_by_telegram_id(42)
    assert user is not None
    sessions = CoffeeSessionRepository(database)
    coffee_session = sessions.create(
        -100,
        user.id,
        datetime(2026, 6, 30, 9, tzinfo=UTC),
    )
    sessions.activate(coffee_session.id, 10)
    services = make_test_services(
        database,
        clock=lambda: datetime(2026, 6, 30, 12, tzinfo=UTC),
    )
    bot = Bot(token="123456:test-token", session=RecordingSession())

    await services.coffee.restore_jobs(bot)

    expired = sessions.require(coffee_session.id)
    assert expired.status == CoffeeSessionStatus.EXPIRED


async def test_request_register_works_in_group_but_is_hidden_from_group_menu(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(
        bot,
        make_update("/request_register", chat_type="group"),
    )

    assert sent_texts(session)[0] == (
        "Запрос на регистрацию отправлен админам. "
        "Теперь администратор сможет зарегистрировать тебя."
    )
    assert "request_register" not in {
        command.name
        for command in services.command_access.visible_commands("group", 42)
    }


async def test_registration_saves_initial_lunch_and_coffee_preferences(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register"))
    await dispatcher.feed_update(bot, make_update("Максим"))
    await dispatcher.feed_update(bot, make_update("Пропустить"))
    await dispatcher.feed_update(bot, make_update("Нет"))
    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("Да"))

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert InvitationPreferenceRepository(database).get(user.id) == InvitationPreferences(
        lunch_enabled=False,
        coffee_enabled=True,
    )
    assert "Звать на ланч: нет.\nЗвать на кофе: да." in sent_texts(session)[0]


async def test_lunch_invitation_setting_works_in_private_and_filters_mentions(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/lunch off"))
    assert sent_texts(session) == ["Приглашения на ланч выключены."]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/lunch"))
    assert sent_texts(session) == [
        "Приглашения на ланч: выключены.\n\n"
        "Изменить настройку: /lunch on или /lunch off."
    ]

    session.clear_messages()
    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    assert sent_texts(session) == ["Время обедать!"]
    assert len(session.sent_polls) == 2


async def test_scheduled_lunch_skips_when_everyone_disabled_lunch_invitations(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    InvitationPreferenceRepository(database).set_lunch_enabled(user.id, False)
    LunchPinRepository(database).upsert(-100, 10, date(2026, 6, 29))
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    services.lunch_auto_chats.enable(-100, "Office")

    await services.lunch_scheduler.run_due_lunch(bot)

    assert sent_texts(session) == []
    assert session.sent_polls == []
    assert [request.message_id for request in session.unpin_requests] == [10]
    assert LunchPinRepository(database).get(-100) is None


async def test_coffee_shout_ignores_user_with_disabled_coffee_invitations(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    activate_user(database, 43, "Анна", "anna")
    anna = UserRepository(database).get_by_telegram_id(43)
    assert anna is not None
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    services = make_test_services(database)
    dispatcher = create_dispatcher(services)

    await dispatcher.feed_update(bot, make_update("/lunch", chat_type="group"))
    attendance_poll_id = session.sent_poll_ids[0]
    await dispatcher.feed_update(
        bot,
        make_poll_answer_update(attendance_poll_id, (1,), user_id=43, username="anna"),
    )
    InvitationPreferenceRepository(database).set_coffee_enabled(anna.id, False)
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/coffee 15", chat_type="group"))

    assert len(session.sent_messages) == 1
    assert "присоединяйтесь на кофе" not in sent_texts(session)[0]

async def test_coffee_recovery_repins_active_card(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    activate_user(database, 42, "Максим", "misha")
    users = UserRepository(database)
    user = users.get_by_telegram_id(42)
    assert user is not None
    sessions = CoffeeSessionRepository(database)
    coffee_session = sessions.create(
        -100,
        user.id,
        datetime(2026, 6, 30, 13, tzinfo=UTC),
    )
    sessions.activate(coffee_session.id, 77)
    services = make_test_services(
        database,
        clock=lambda: datetime(2026, 6, 30, 12, tzinfo=UTC),
    )
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)

    await services.coffee.restore_jobs(bot)

    assert len(session.pin_requests) == 1
    assert session.pin_requests[0].message_id == 77
    assert session.pin_requests[0].disable_notification is True
