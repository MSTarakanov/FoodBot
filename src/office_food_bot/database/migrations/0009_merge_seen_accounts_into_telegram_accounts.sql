CREATE TABLE telegram_accounts_new (
    telegram_user_id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO telegram_accounts_new (
    telegram_user_id,
    user_id,
    username,
    first_name,
    last_name,
    first_seen_at,
    last_seen_at,
    updated_at
)
SELECT
    telegram_user_id,
    user_id,
    username,
    first_name,
    last_name,
    updated_at,
    updated_at,
    updated_at
FROM telegram_accounts;

INSERT INTO telegram_accounts_new (
    telegram_user_id,
    user_id,
    username,
    first_name,
    last_name,
    first_seen_at,
    last_seen_at,
    updated_at
)
SELECT
    telegram_seen_accounts.telegram_user_id,
    NULL,
    telegram_seen_accounts.username,
    telegram_seen_accounts.first_name,
    telegram_seen_accounts.last_name,
    telegram_seen_accounts.first_seen_at,
    telegram_seen_accounts.last_seen_at,
    CURRENT_TIMESTAMP
FROM telegram_seen_accounts
LEFT JOIN telegram_accounts
    ON telegram_accounts.telegram_user_id = telegram_seen_accounts.telegram_user_id
WHERE telegram_accounts.telegram_user_id IS NULL;

UPDATE telegram_accounts_new
SET
    username = (
        SELECT telegram_seen_accounts.username
        FROM telegram_seen_accounts
        WHERE telegram_seen_accounts.telegram_user_id = telegram_accounts_new.telegram_user_id
    ),
    first_name = (
        SELECT telegram_seen_accounts.first_name
        FROM telegram_seen_accounts
        WHERE telegram_seen_accounts.telegram_user_id = telegram_accounts_new.telegram_user_id
    ),
    last_name = (
        SELECT telegram_seen_accounts.last_name
        FROM telegram_seen_accounts
        WHERE telegram_seen_accounts.telegram_user_id = telegram_accounts_new.telegram_user_id
    ),
    first_seen_at = (
        SELECT telegram_seen_accounts.first_seen_at
        FROM telegram_seen_accounts
        WHERE telegram_seen_accounts.telegram_user_id = telegram_accounts_new.telegram_user_id
    ),
    last_seen_at = (
        SELECT telegram_seen_accounts.last_seen_at
        FROM telegram_seen_accounts
        WHERE telegram_seen_accounts.telegram_user_id = telegram_accounts_new.telegram_user_id
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE EXISTS (
    SELECT 1
    FROM telegram_seen_accounts
    WHERE telegram_seen_accounts.telegram_user_id = telegram_accounts_new.telegram_user_id
);

DROP TABLE telegram_accounts;
ALTER TABLE telegram_accounts_new RENAME TO telegram_accounts;
DROP TABLE telegram_seen_accounts;
