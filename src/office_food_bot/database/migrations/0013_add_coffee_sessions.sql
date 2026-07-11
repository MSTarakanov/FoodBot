CREATE TABLE coffee_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    invitations_enabled INTEGER NOT NULL DEFAULT 1
        CHECK (invitations_enabled IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE coffee_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    message_id INTEGER,
    initiator_user_id INTEGER NOT NULL REFERENCES users(id),
    last_proposer_user_id INTEGER NOT NULL REFERENCES users(id),
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'creating', 'active', 'completing', 'completed', 'expired', 'failed'
    )),
    notification_attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    retry_until TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE UNIQUE INDEX one_open_coffee_session_per_chat
ON coffee_sessions (chat_id)
WHERE status IN ('creating', 'active');

CREATE TABLE coffee_session_participants (
    session_id INTEGER NOT NULL REFERENCES coffee_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, user_id)
);
