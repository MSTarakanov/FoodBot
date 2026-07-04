from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendPoll, SetMyCommands, TelegramMethod
from aiogram.methods.send_message import SendMessage
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    Chat,
    Message,
    ReplyKeyboardMarkup,
    Update,
    User,
)

from office_food_bot.app import create_dispatcher, create_services
from office_food_bot.commands import setup_bot_commands
from office_food_bot.commands.definitions import (
    ADMIN_COMMANDS,
    ADMIN_HELP_TEXT,
    PUBLIC_COMMANDS,
    PUBLIC_HELP_TEXT,
    START_TEXT,
)
from office_food_bot.config import RuntimeEnvironment, Settings
from office_food_bot.database import Database
from office_food_bot.models import SplitwiseBalance, SplitwiseMember, UserStatus
from office_food_bot.repositories import UserRepository
from office_food_bot.services.lunch import (
    LUNCH_PLACE_POLL_OPTIONS,
    LUNCH_PLACE_POLL_QUESTION,
    LUNCH_POLL_OPTIONS,
    LUNCH_POLL_QUESTION,
)
from office_food_bot.services.splitwise import SplitwiseUnavailableError

DEFAULT_ADMIN_IDS = frozenset({7})
DEFAULT_SPLITWISE_GROUP_ID = 55


@dataclass(frozen=True)
class ChatCommandMenu:
    chat_id: int
    commands: tuple[BotCommand, ...]


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.sent_messages: list[SendMessage] = []
        self.sent_polls: list[SendPoll] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Message],
        timeout: int | None = None,
    ) -> Message:
        if isinstance(method, SendMessage):
            self.sent_messages.append(method)
            return _send_message_response(method, len(self.sent_messages) + len(self.sent_polls))
        if isinstance(method, SendPoll):
            self.sent_polls.append(method)
            return _send_poll_response(method, len(self.sent_messages) + len(self.sent_polls))

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


class RecordingCommandMenuClient:
    def __init__(self) -> None:
        self.public_command_menus: list[tuple[BotCommand, ...]] = []
        self.chat_command_menus: list[ChatCommandMenu] = []

    async def set_my_commands(
        self,
        commands: list[BotCommand],
        scope: BotCommandScopeChat | None = None,
    ) -> bool:
        command_menu = tuple(commands)
        if scope is None:
            self.public_command_menus.append(command_menu)
            return True

        chat_id = scope.chat_id
        if not isinstance(chat_id, int):
            raise AssertionError(f"Expected numeric admin chat id, got {chat_id!r}")

        self.chat_command_menus.append(ChatCommandMenu(chat_id=chat_id, commands=command_menu))
        return True


class AdminChatNotFoundCommandMenuClient(RecordingCommandMenuClient):
    async def set_my_commands(
        self,
        commands: list[BotCommand],
        scope: BotCommandScopeChat | None = None,
    ) -> bool:
        if scope is not None:
            raise TelegramBadRequest(
                method=SetMyCommands(commands=commands, scope=scope),
                message="Bad Request: chat not found",
            )

        return await super().set_my_commands(commands, scope)


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
    )


def make_update(
    text: str,
    user_id: int = 42,
    first_name: str = "Misha",
    username: str | None = "misha",
    last_name: str | None = None,
) -> Update:
    user = User(
        id=user_id,
        is_bot=False,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )
    chat = Chat(id=user_id, type="private")
    message = Message(
        message_id=100,
        date=datetime.now(tz=UTC),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=1, message=message)


def make_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.sqlite3")
    database.init_schema()
    return database


def make_dispatcher(
    database: Database,
    admin_ids: frozenset[int] = DEFAULT_ADMIN_IDS,
    splitwise_members: tuple[SplitwiseMember, ...] = (),
    splitwise_unavailable: bool = False,
) -> Dispatcher:
    settings = Settings(
        environment=RuntimeEnvironment.DEVELOPMENT,
        telegram_bot_token="123456:test-token",
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
        clock=lambda: datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
        splitwise_client=FakeSplitwiseClient(
            splitwise_members,
            unavailable=splitwise_unavailable,
        ),
    )
    return create_dispatcher(services)


def sent_texts(session: RecordingSession) -> list[str]:
    return [message.text for message in session.sent_messages]


def keyboard_texts(message: SendMessage) -> list[list[str]]:
    reply_markup = message.reply_markup
    assert isinstance(reply_markup, ReplyKeyboardMarkup)
    return [[button.text for button in row] for row in reply_markup.keyboard]


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


@pytest.mark.parametrize(
    ("incoming_text", "expected_text"),
    [
        ("/start", START_TEXT),
        ("/help", PUBLIC_HELP_TEXT),
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


async def test_help_shows_admin_commands_to_admins(tmp_path: Path) -> None:
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    database = make_database(tmp_path)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/help", user_id=7, first_name="Admin"))

    assert sent_texts(session) == [ADMIN_HELP_TEXT]


async def test_setup_bot_commands_registers_telegram_menu() -> None:
    bot = RecordingCommandMenuClient()

    await setup_bot_commands(bot, DEFAULT_ADMIN_IDS)

    assert len(bot.public_command_menus) == 1
    assert len(bot.chat_command_menus) == 1

    public_commands = bot.public_command_menus[0]
    assert [command.command for command in public_commands] == [
        definition.name for definition in PUBLIC_COMMANDS
    ]
    assert [command.command for command in public_commands] == [
        "start",
        "help",
        "hi",
        "register",
        "cancel",
        "meta",
        "balance",
        "lunch",
    ]

    admin_menu = bot.chat_command_menus[0]
    assert admin_menu.chat_id == 7
    assert [command.command for command in admin_menu.commands] == [
        definition.name for definition in ADMIN_COMMANDS
    ]
    assert "approve" in [command.command for command in admin_menu.commands]


async def test_setup_bot_commands_ignores_missing_admin_chat() -> None:
    bot = AdminChatNotFoundCommandMenuClient()

    await setup_bot_commands(bot, DEFAULT_ADMIN_IDS)

    assert len(bot.public_command_menus) == 1
    assert len(bot.chat_command_menus) == 0


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

    texts = sent_texts(session)
    assert texts[0] == (
        "Заявка на регистрацию отправлена. Жду аппрув.\n\n"
        "Splitwise найден: max@example.com (ID 1001)."
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

    texts = sent_texts(session)
    assert texts[0] == (
        "Заявка на регистрацию отправлена. Жду аппрув.\n\n"
        "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
        "без привязки."
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

    assert sent_texts(session) == [PUBLIC_HELP_TEXT]

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

    assert sent_texts(session) == ["Не могу: аппрувить могут только админы."]


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

    assert sent_texts(session) == ["Не могу: список заявок доступен только админам."]


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

    await dispatcher.feed_update(bot, make_update("/meta 25"))

    assert sent_texts(session) == ["Максим будет в 12:40"]


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
    await dispatcher.feed_update(bot, make_update("/meta 25"))
    assert sent_texts(session) == ["Максим будет в 12:40"]


async def test_meta_requires_approved_registration(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/meta 25"))

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
        "Текущая ситуация по балансам в Splitwise:\n"
        "\n"
        "🔴 Антон: -10837.88 RSD\n"
        "⚪ Максим: +277.97 RSD\n"
        "🟢 Тимофей: +18976.74 RSD"
    ]


async def test_lunch_requires_registered_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/lunch"))

    assert sent_texts(session) == ["Сначала зарегистрируйся: /register"]
    assert session.sent_polls == []


async def test_lunch_requires_active_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch"))

    assert sent_texts(session) == ["Регистрация еще ждет аппрува."]
    assert session.sent_polls == []


async def test_lunch_creates_non_anonymous_polls_for_active_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await submit_registration(dispatcher, bot, session)
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.clear_messages()

    await dispatcher.feed_update(bot, make_update("/lunch"))

    assert sent_texts(session) == []
    assert len(session.sent_polls) == 2

    lunch_poll = session.sent_polls[0]
    assert lunch_poll.question == LUNCH_POLL_QUESTION
    assert poll_option_texts(lunch_poll) == list(LUNCH_POLL_OPTIONS)
    assert lunch_poll.is_anonymous is False
    assert lunch_poll.allows_multiple_answers is False
    assert lunch_poll.allow_adding_options is True

    place_poll = session.sent_polls[1]
    assert place_poll.question == LUNCH_PLACE_POLL_QUESTION
    assert poll_option_texts(place_poll) == list(LUNCH_PLACE_POLL_OPTIONS)
    assert place_poll.is_anonymous is False
    assert place_poll.allows_multiple_answers is False
    assert place_poll.allow_adding_options is True
