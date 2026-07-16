from __future__ import annotations

import sqlite3
from datetime import date

from office_food_bot.database import Database
from office_food_bot.features.vacation.models import UserVacation
from office_food_bot.features.vacation.queries import (
    DELETE_USER_VACATION_SQL,
    GET_USER_VACATION_SQL,
    LIST_ACTIVE_VACATION_USER_IDS_SQL,
    UPSERT_USER_VACATION_SQL,
)


class VacationRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, user_id: int) -> UserVacation | None:
        row = self._database.connection.execute(
            GET_USER_VACATION_SQL,
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return _user_vacation_from_row(row)

    def set_until_date(self, user_id: int, until_date: date) -> UserVacation:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_USER_VACATION_SQL,
                (user_id, until_date.isoformat()),
            )

        vacation = self.get(user_id)
        if vacation is None:
            raise RuntimeError("Saved vacation was not found")
        return vacation

    def clear(self, user_id: int) -> None:
        with self._database.connection:
            self._database.connection.execute(DELETE_USER_VACATION_SQL, (user_id,))

    def active_user_ids(self, today: date) -> frozenset[int]:
        rows = self._database.connection.execute(
            LIST_ACTIVE_VACATION_USER_IDS_SQL,
            (today.isoformat(),),
        ).fetchall()
        return frozenset(int(row["user_id"]) for row in rows)


def _user_vacation_from_row(row: sqlite3.Row) -> UserVacation:
    return UserVacation(
        user_id=int(row["user_id"]),
        until_date=date.fromisoformat(str(row["until_date"])),
    )
