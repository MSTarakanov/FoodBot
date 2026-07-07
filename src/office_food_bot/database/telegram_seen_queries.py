UPSERT_TELEGRAM_SEEN_ACCOUNT_SQL = """
INSERT INTO telegram_seen_accounts (
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
    last_seen_at = CURRENT_TIMESTAMP
"""

GET_TELEGRAM_SEEN_ACCOUNT_SQL = """
SELECT
    telegram_user_id,
    username,
    first_name,
    last_name
FROM telegram_seen_accounts
WHERE telegram_user_id = ?
"""

LIST_UNREGISTERED_TELEGRAM_SEEN_ACCOUNTS_SQL = """
SELECT
    telegram_seen_accounts.telegram_user_id,
    telegram_seen_accounts.username,
    telegram_seen_accounts.first_name,
    telegram_seen_accounts.last_name
FROM telegram_seen_accounts
LEFT JOIN telegram_accounts
    ON telegram_accounts.telegram_user_id = telegram_seen_accounts.telegram_user_id
WHERE telegram_accounts.telegram_user_id IS NULL
ORDER BY telegram_seen_accounts.last_seen_at DESC, telegram_seen_accounts.telegram_user_id
LIMIT ?
"""
