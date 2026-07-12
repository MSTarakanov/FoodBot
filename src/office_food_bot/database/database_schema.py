USERS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'rejected', 'disabled', 'abandoned')),
    role TEXT NOT NULL DEFAULT 'member'
        CHECK (role IN ('member', 'admin')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

SCHEMA_SQL = f"""
PRAGMA foreign_keys = ON;

{USERS_SCHEMA_SQL};

CREATE TABLE IF NOT EXISTS telegram_accounts (
    telegram_user_id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registration_requests (
    telegram_user_id INTEGER PRIMARY KEY REFERENCES telegram_accounts(telegram_user_id)
        ON DELETE CASCADE,
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS splitwise_users (
    splitwise_user_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS telegram_debug_settings (
    telegram_user_id INTEGER PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lunch_auto_chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lunch_pinned_messages (
    chat_id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL,
    lunch_date TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_vacations (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    until_date TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS polls (
    poll_id TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    context_date TEXT NOT NULL,
    published_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS polls_chat_date_kind_idx
ON polls (chat_id, context_date, kind, published_at DESC);

CREATE TABLE IF NOT EXISTS poll_selected_options (
    poll_id TEXT NOT NULL REFERENCES polls(poll_id) ON DELETE CASCADE,
    telegram_user_id INTEGER NOT NULL,
    option_key TEXT NOT NULL,
    selected_at TEXT NOT NULL,
    PRIMARY KEY (poll_id, telegram_user_id, option_key)
);

CREATE TABLE IF NOT EXISTS coffee_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    invitations_enabled INTEGER NOT NULL DEFAULT 1
        CHECK (invitations_enabled IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coffee_sessions (
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

CREATE UNIQUE INDEX IF NOT EXISTS one_open_coffee_session_per_chat
ON coffee_sessions (chat_id)
WHERE status IN ('creating', 'active');

CREATE TABLE IF NOT EXISTS coffee_session_participants (
    session_id INTEGER NOT NULL REFERENCES coffee_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, user_id)
);
"""

SPLITWISE_USERS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS splitwise_users (
    splitwise_user_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""
