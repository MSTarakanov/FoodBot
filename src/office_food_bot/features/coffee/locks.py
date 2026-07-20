from __future__ import annotations

import asyncio


class CoffeeChatLocks:
    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}

    def for_chat(self, chat_id: int) -> asyncio.Lock:
        return self._locks.setdefault(chat_id, asyncio.Lock())
