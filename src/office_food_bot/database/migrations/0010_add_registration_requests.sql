CREATE TABLE IF NOT EXISTS registration_requests (
    telegram_user_id INTEGER PRIMARY KEY REFERENCES telegram_accounts(telegram_user_id)
        ON DELETE CASCADE,
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
