GET_INVITATION_PREFERENCES_SQL = """
SELECT lunch_invitations_enabled, coffee_invitations_enabled
FROM user_invitation_preferences
WHERE user_id = ?
"""

UPSERT_INVITATION_PREFERENCES_SQL = """
INSERT INTO user_invitation_preferences (
    user_id,
    lunch_invitations_enabled,
    coffee_invitations_enabled,
    updated_at
)
VALUES (?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(user_id) DO UPDATE SET
    lunch_invitations_enabled = excluded.lunch_invitations_enabled,
    coffee_invitations_enabled = excluded.coffee_invitations_enabled,
    updated_at = CURRENT_TIMESTAMP
"""

UPSERT_LUNCH_INVITATION_PREFERENCE_SQL = """
INSERT INTO user_invitation_preferences (
    user_id,
    lunch_invitations_enabled,
    coffee_invitations_enabled,
    updated_at
)
VALUES (?, ?, 1, CURRENT_TIMESTAMP)
ON CONFLICT(user_id) DO UPDATE SET
    lunch_invitations_enabled = excluded.lunch_invitations_enabled,
    updated_at = CURRENT_TIMESTAMP
"""

UPSERT_COFFEE_INVITATION_PREFERENCE_SQL = """
INSERT INTO user_invitation_preferences (
    user_id,
    lunch_invitations_enabled,
    coffee_invitations_enabled,
    updated_at
)
VALUES (?, 1, ?, CURRENT_TIMESTAMP)
ON CONFLICT(user_id) DO UPDATE SET
    coffee_invitations_enabled = excluded.coffee_invitations_enabled,
    updated_at = CURRENT_TIMESTAMP
"""
