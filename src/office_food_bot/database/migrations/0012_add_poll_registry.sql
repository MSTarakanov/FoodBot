CREATE TABLE polls (
    poll_id TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    context_date TEXT NOT NULL,
    published_at TEXT NOT NULL
);

CREATE INDEX polls_chat_date_kind_idx
ON polls (chat_id, context_date, kind, published_at DESC);

CREATE TABLE poll_selected_options (
    poll_id TEXT NOT NULL REFERENCES polls(poll_id) ON DELETE CASCADE,
    telegram_user_id INTEGER NOT NULL,
    option_key TEXT NOT NULL,
    selected_at TEXT NOT NULL,
    PRIMARY KEY (poll_id, telegram_user_id, option_key)
);
