from __future__ import annotations

from office_food_bot.database import Database
from office_food_bot.features.invitations.models import InvitationPreferences
from office_food_bot.features.invitations.queries import (
    GET_INVITATION_PREFERENCES_SQL,
    UPSERT_COFFEE_INVITATION_PREFERENCE_SQL,
    UPSERT_INVITATION_PREFERENCES_SQL,
    UPSERT_LUNCH_INVITATION_PREFERENCE_SQL,
)


class InvitationPreferenceRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, user_id: int) -> InvitationPreferences:
        row = self._database.connection.execute(
            GET_INVITATION_PREFERENCES_SQL,
            (user_id,),
        ).fetchone()
        if row is None:
            return InvitationPreferences()
        return InvitationPreferences(
            lunch_enabled=bool(row["lunch_invitations_enabled"]),
            coffee_enabled=bool(row["coffee_invitations_enabled"]),
        )

    def save(self, user_id: int, preferences: InvitationPreferences) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_INVITATION_PREFERENCES_SQL,
                (
                    user_id,
                    int(preferences.lunch_enabled),
                    int(preferences.coffee_enabled),
                ),
            )

    def set_lunch_enabled(self, user_id: int, enabled: bool) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_LUNCH_INVITATION_PREFERENCE_SQL,
                (user_id, int(enabled)),
            )

    def set_coffee_enabled(self, user_id: int, enabled: bool) -> None:
        with self._database.connection:
            self._database.connection.execute(
                UPSERT_COFFEE_INVITATION_PREFERENCE_SQL,
                (user_id, int(enabled)),
            )
