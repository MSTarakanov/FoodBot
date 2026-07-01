GET_USER_BY_TELEGRAM_ID_SQL = """
SELECT
    users.id,
    users.display_name,
    users.status,
    users.role,
    telegram_accounts.telegram_user_id,
    telegram_accounts.username,
    telegram_accounts.first_name,
    telegram_accounts.last_name
FROM telegram_accounts
JOIN users ON users.id = telegram_accounts.user_id
WHERE telegram_accounts.telegram_user_id = ?
"""

LIST_PENDING_USERS_SQL = """
SELECT
    users.id,
    users.display_name,
    users.status,
    users.role,
    telegram_accounts.telegram_user_id,
    telegram_accounts.username,
    telegram_accounts.first_name,
    telegram_accounts.last_name
FROM telegram_accounts
JOIN users ON users.id = telegram_accounts.user_id
WHERE users.status = ?
ORDER BY users.created_at, users.id
"""

INSERT_USER_SQL = """
INSERT INTO users (display_name, status, role)
VALUES (?, ?, ?)
"""

INSERT_TELEGRAM_ACCOUNT_SQL = """
INSERT INTO telegram_accounts (
    telegram_user_id,
    user_id,
    username,
    first_name,
    last_name
)
VALUES (?, ?, ?, ?, ?)
"""

UPDATE_TELEGRAM_PROFILE_SQL = """
UPDATE telegram_accounts
SET username = ?,
    first_name = ?,
    last_name = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE telegram_user_id = ?
"""

APPROVE_USER_BY_TELEGRAM_ID_SQL = """
UPDATE users
SET status = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = (
    SELECT user_id
    FROM telegram_accounts
    WHERE telegram_user_id = ?
)
"""

COUNT_SPLITWISE_USERS_SQL = "SELECT COUNT(*) FROM splitwise_users"
