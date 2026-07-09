CREATE TABLE IF NOT EXISTS lunch_pinned_messages (
    chat_id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL,
    lunch_date TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
