UPSERT_REGISTRATION_REQUEST_SQL = """
INSERT INTO registration_requests (telegram_user_id)
VALUES (?)
ON CONFLICT(telegram_user_id) DO UPDATE SET
    requested_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
"""

DELETE_REGISTRATION_REQUEST_SQL = """
DELETE FROM registration_requests
WHERE telegram_user_id = ?
"""

LIST_REQUESTED_REGISTRATION_ACCOUNTS_SQL = """
SELECT
    telegram_accounts.telegram_user_id,
    telegram_accounts.username,
    telegram_accounts.first_name,
    telegram_accounts.last_name
FROM registration_requests
JOIN telegram_accounts
    ON telegram_accounts.telegram_user_id = registration_requests.telegram_user_id
LEFT JOIN users
    ON users.id = telegram_accounts.user_id
WHERE telegram_accounts.user_id IS NULL
    OR users.status = ?
ORDER BY registration_requests.requested_at DESC, telegram_accounts.telegram_user_id
LIMIT ?
"""
