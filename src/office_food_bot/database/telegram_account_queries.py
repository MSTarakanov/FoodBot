UPSERT_TELEGRAM_ACCOUNT_PROFILE_SQL = """
INSERT INTO telegram_accounts (
    telegram_user_id,
    username,
    first_name,
    last_name
)
VALUES (?, ?, ?, ?)
ON CONFLICT(telegram_user_id) DO UPDATE SET
    username = excluded.username,
    first_name = excluded.first_name,
    last_name = excluded.last_name,
    last_seen_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
"""

GET_TELEGRAM_ACCOUNT_SQL = """
SELECT
    telegram_user_id,
    username,
    first_name,
    last_name
FROM telegram_accounts
WHERE telegram_user_id = ?
"""

LIST_UNREGISTERED_TELEGRAM_ACCOUNTS_SQL = """
SELECT
    telegram_accounts.telegram_user_id,
    telegram_accounts.username,
    telegram_accounts.first_name,
    telegram_accounts.last_name
FROM telegram_accounts
LEFT JOIN users
    ON users.id = telegram_accounts.user_id
WHERE telegram_accounts.user_id IS NULL
    OR users.status = ?
ORDER BY telegram_accounts.last_seen_at DESC, telegram_accounts.telegram_user_id
LIMIT ?
"""
