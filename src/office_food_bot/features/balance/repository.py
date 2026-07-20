from __future__ import annotations

import sqlite3

from office_food_bot.application.users.models import UserStatus
from office_food_bot.database import Database
from office_food_bot.features.balance.models import ActiveSplitwiseUser

LIST_ACTIVE_SPLITWISE_USERS_SQL = """
SELECT
    telegram_accounts.username,
    users.display_name,
    splitwise_users.splitwise_user_id,
    splitwise_users.email AS splitwise_email
FROM users
JOIN splitwise_users ON splitwise_users.user_id = users.id
JOIN telegram_accounts ON telegram_accounts.user_id = users.id
WHERE users.status = ?
ORDER BY users.display_name, users.id
"""


class BalanceRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_active_splitwise_users(self) -> tuple[ActiveSplitwiseUser, ...]:
        rows = self._database.connection.execute(
            LIST_ACTIVE_SPLITWISE_USERS_SQL,
            (UserStatus.ACTIVE.value,),
        ).fetchall()
        return tuple(_active_splitwise_user_from_row(row) for row in rows)


def _active_splitwise_user_from_row(row: sqlite3.Row) -> ActiveSplitwiseUser:
    return ActiveSplitwiseUser(
        username=_optional_str(row["username"]),
        display_name=str(row["display_name"]),
        splitwise_user_id=int(row["splitwise_user_id"]),
        email=_optional_str(row["splitwise_email"]),
    )


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)
