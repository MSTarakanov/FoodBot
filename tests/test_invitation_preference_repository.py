from office_food_bot.application.users.models import TelegramProfile
from office_food_bot.database import Database
from office_food_bot.features.invitations.models import InvitationPreferences
from office_food_bot.features.invitations.repository import InvitationPreferenceRepository
from office_food_bot.infrastructure.persistence.users import UserRepository


def test_invitation_preferences_default_to_enabled_and_persist(
    database: Database,
) -> None:
    user = UserRepository(database).create_pending_user(
        TelegramProfile(42, "misha", "Misha", None),
        "Максим",
    )
    preferences = InvitationPreferenceRepository(database)

    assert preferences.get(user.id) == InvitationPreferences()

    preferences.save(user.id, InvitationPreferences(False, False))
    assert preferences.get(user.id) == InvitationPreferences(False, False)

    preferences.set_lunch_enabled(user.id, True)
    assert preferences.get(user.id) == InvitationPreferences(True, False)

    preferences.set_coffee_enabled(user.id, True)
    assert preferences.get(user.id) == InvitationPreferences(True, True)
