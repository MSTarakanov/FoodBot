CREATE TABLE user_invitation_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    lunch_invitations_enabled INTEGER NOT NULL DEFAULT 1
        CHECK (lunch_invitations_enabled IN (0, 1)),
    coffee_invitations_enabled INTEGER NOT NULL DEFAULT 1
        CHECK (coffee_invitations_enabled IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO user_invitation_preferences (
    user_id,
    lunch_invitations_enabled,
    coffee_invitations_enabled,
    updated_at
)
SELECT user_id, 1, invitations_enabled, updated_at
FROM coffee_preferences;

DROP TABLE coffee_preferences;
