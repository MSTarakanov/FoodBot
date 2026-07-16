from __future__ import annotations

from collections.abc import Sequence

from office_food_bot.application.users.models import RegisteredUser

LUNCH_ANNOUNCEMENT_TEXT = "Время обедать!"


def lunch_announcement_text(active_users: Sequence[RegisteredUser]) -> str:
    tags = tuple(
        f"@{user.username}"
        for user in active_users
        if user.username is not None
    )
    if not tags:
        return LUNCH_ANNOUNCEMENT_TEXT
    return f"{LUNCH_ANNOUNCEMENT_TEXT} {' '.join(tags)}"
