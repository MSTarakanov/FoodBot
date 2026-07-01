from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar, cast
from zoneinfo import ZoneInfo

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.send_message import SendMessage
from aiogram.methods.set_my_commands import SetMyCommands
from aiogram.types import BotCommandScopeChat, Chat, Message, Update, User

from office_food_bot.app import create_dispatcher, create_services
from office_food_bot.commands import setup_bot_commands
from office_food_bot.commands.definitions import (
    ADMIN_COMMANDS,
    ADMIN_HELP_TEXT,
    PUBLIC_COMMANDS,
    PUBLIC_HELP_TEXT,
    START_TEXT,
)
from office_food_bot.config import Settings
from office_food_bot.database import Database
from office_food_bot.models import UserStatus
from office_food_bot.repositories import UserRepository

DEFAULT_ADMIN_IDS = frozenset({7})
TelegramResponse = TypeVar("TelegramResponse")


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[object] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramResponse],
        timeout: int | None = None,
    ) -> TelegramResponse:
        self.requests.append(method)
        if isinstance(method, SendMessage):
            return cast(
                TelegramResponse,
                Message(
                    message_id=len(self.requests),
                    date=datetime.now(tz=UTC),
                    chat=Chat(id=method.chat_id, type="private"),
                    text=method.text,
                ),
            )
        if isinstance(method, SetMyCommands):
            return cast(TelegramResponse, True)
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


def make_update(
    text: str,
    user_id: int = 42,
    first_name: str = "Misha",
    username: str | None = "misha",
) -> Update:
    user = User(id=user_id, is_bot=False, first_name=first_name, username=username)
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
) -> Dispatcher:
    settings = Settings(
        telegram_bot_token="123456:test-token",
        database_path=database.path,
        telegram_admin_ids=admin_ids,
        timezone="Europe/Belgrade",
    )
    services = create_services(
        database,
        settings,
        clock=lambda: datetime(2026, 6, 30, 12, 15, tzinfo=ZoneInfo("Europe/Belgrade")),
    )
    return create_dispatcher(services)


def sent_texts(session: RecordingSession) -> list[str]:
    return [str(request.text) for request in session.requests if isinstance(request, SendMessage)]


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

    assert len(session.requests) == 1
    request = session.requests[0]
    assert isinstance(request, SendMessage)
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
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)

    await setup_bot_commands(bot, DEFAULT_ADMIN_IDS)

    assert len(session.requests) == 2

    public_request = session.requests[0]
    assert isinstance(public_request, SetMyCommands)
    assert public_request.scope is None
    assert [command.command for command in public_request.commands] == [
        definition.name for definition in PUBLIC_COMMANDS
    ]
    assert [command.command for command in public_request.commands] == [
        "start",
        "help",
        "hi",
        "register",
        "meta",
        "balance",
    ]

    admin_request = session.requests[1]
    assert isinstance(admin_request, SetMyCommands)
    assert isinstance(admin_request.scope, BotCommandScopeChat)
    assert admin_request.scope.chat_id == 7
    assert [command.command for command in admin_request.commands] == [
        definition.name for definition in ADMIN_COMMANDS
    ]
    assert "approve" in [command.command for command in admin_request.commands]


async def test_register_creates_pending_user_and_notifies_admin(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))

    texts = sent_texts(session)
    assert texts[0] == "Заявка на регистрацию отправлена. Жду аппрув."
    assert "Новая регистрация" in texts[1]
    assert "Имя: Максим" in texts[1]
    assert "Аппрув: /approve 42" in texts[1]

    user = UserRepository(database).get_by_telegram_id(42)
    assert user is not None
    assert user.display_name == "Максим"
    assert user.status == UserStatus.PENDING


async def test_register_does_not_duplicate_existing_pending_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    session.requests.clear()
    await dispatcher.feed_update(bot, make_update("/register Другое"))

    assert sent_texts(session) == ["Заявка уже ждет аппрува, Максим"]


async def test_register_existing_active_user_replies_with_name(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.requests.clear()

    await dispatcher.feed_update(bot, make_update("/register Другое"))

    assert sent_texts(session) == ["Уже зарегистрирован, Максим"]


async def test_admin_can_approve_pending_user(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    session.requests.clear()
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

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    session.requests.clear()
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=99, first_name="NotAdmin"))

    assert sent_texts(session) == ["Не могу: аппрувить могут только админы."]


async def test_meta_uses_registered_display_name(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.requests.clear()

    await dispatcher.feed_update(bot, make_update("/meta 25"))

    assert sent_texts(session) == ["Максим будет в 12:40"]


async def test_registration_happy_path_allows_meta_after_approval(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    assert sent_texts(session)[0] == "Заявка на регистрацию отправлена. Жду аппрув."
    assert "Аппрув: /approve 42" in sent_texts(session)[1]

    session.requests.clear()
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    assert sent_texts(session) == [
        "Аппрувнул: Максим",
        "Регистрация подтверждена. Теперь я буду звать тебя Максим.",
    ]

    session.requests.clear()
    await dispatcher.feed_update(bot, make_update("/meta 25"))
    assert sent_texts(session) == ["Максим будет в 12:40"]


async def test_meta_requires_approved_registration(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    session.requests.clear()

    await dispatcher.feed_update(bot, make_update("/meta 25"))

    assert sent_texts(session) == ["Регистрация еще ждет аппрува."]


async def test_balance_requires_active_user_and_has_placeholder(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    session = RecordingSession()
    bot = Bot(token="123456:test-token", session=session)
    dispatcher = make_dispatcher(database)

    await dispatcher.feed_update(bot, make_update("/register Максим"))
    await dispatcher.feed_update(bot, make_update("/approve 42", user_id=7, first_name="Admin"))
    session.requests.clear()

    await dispatcher.feed_update(bot, make_update("/balance"))

    assert sent_texts(session) == ["Splitwise пока не подключен."]
