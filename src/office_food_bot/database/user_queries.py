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

GET_USER_BY_ID_SQL = """
SELECT
    users.id,
    users.display_name,
    users.status,
    users.role,
    telegram_accounts.telegram_user_id,
    telegram_accounts.username,
    telegram_accounts.first_name,
    telegram_accounts.last_name
FROM users
JOIN telegram_accounts ON telegram_accounts.user_id = users.id
WHERE users.id = ?
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

LIST_ACTIVE_USERS_SQL = """
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
ORDER BY users.display_name, users.id
"""

LIST_PENDING_REGISTRATIONS_SQL = """
SELECT
    users.id,
    users.display_name,
    users.status,
    users.role,
    telegram_accounts.telegram_user_id,
    telegram_accounts.username,
    telegram_accounts.first_name,
    telegram_accounts.last_name,
    splitwise_users.splitwise_user_id,
    splitwise_users.email AS splitwise_email
FROM telegram_accounts
JOIN users ON users.id = telegram_accounts.user_id
LEFT JOIN splitwise_users ON splitwise_users.user_id = users.id
WHERE users.status = ?
ORDER BY users.created_at, users.id
"""

LIST_ACTIVE_SPLITWISE_USERS_SQL = """
SELECT
    users.display_name,
    splitwise_users.splitwise_user_id,
    splitwise_users.email AS splitwise_email
FROM users
JOIN splitwise_users ON splitwise_users.user_id = users.id
WHERE users.status = ?
ORDER BY users.display_name, users.id
"""

GET_REGISTRATION_DETAILS_BY_TELEGRAM_ID_SQL = """
SELECT
    users.display_name,
    splitwise_users.splitwise_user_id,
    splitwise_users.email AS splitwise_email
FROM telegram_accounts
JOIN users ON users.id = telegram_accounts.user_id
LEFT JOIN splitwise_users ON splitwise_users.user_id = users.id
WHERE telegram_accounts.telegram_user_id = ?
"""

INSERT_USER_SQL = """
INSERT INTO users (display_name, status, role)
VALUES (?, ?, ?)
"""

UPSERT_LINKED_TELEGRAM_ACCOUNT_SQL = """
INSERT INTO telegram_accounts (
    telegram_user_id,
    user_id,
    username,
    first_name,
    last_name
)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(telegram_user_id) DO UPDATE SET
    user_id = excluded.user_id,
    username = excluded.username,
    first_name = excluded.first_name,
    last_name = excluded.last_name,
    last_seen_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
"""

UPDATE_TELEGRAM_PROFILE_SQL = """
UPDATE telegram_accounts
SET username = ?,
    first_name = ?,
    last_name = ?,
    last_seen_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE telegram_user_id = ?
"""

UPDATE_USER_REGISTRATION_BY_TELEGRAM_ID_SQL = """
UPDATE users
SET display_name = ?,
    status = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = (
    SELECT user_id
    FROM telegram_accounts
    WHERE telegram_user_id = ?
)
"""

DELETE_SPLITWISE_USER_BY_USER_ID_SQL = """
DELETE FROM splitwise_users
WHERE user_id = ?
"""

INSERT_SPLITWISE_USER_SQL = """
INSERT INTO splitwise_users (
    splitwise_user_id,
    user_id,
    email
)
VALUES (?, ?, ?)
"""

UPDATE_USER_STATUS_BY_TELEGRAM_ID_SQL = """
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
