INSERT_POLL_SQL = """
INSERT INTO polls (poll_id, chat_id, message_id, kind, context_date, published_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(poll_id) DO UPDATE SET
    chat_id = excluded.chat_id,
    message_id = excluded.message_id,
    kind = excluded.kind,
    context_date = excluded.context_date,
    published_at = excluded.published_at
"""

GET_POLL_SQL = """
SELECT poll_id, chat_id, message_id, kind, context_date, published_at
FROM polls
WHERE poll_id = ?
"""

GET_LATEST_POLL_SQL = """
SELECT poll_id, chat_id, message_id, kind, context_date, published_at
FROM polls
WHERE chat_id = ? AND context_date = ? AND kind IN ({kind_placeholders})
ORDER BY published_at DESC, rowid DESC
LIMIT 1
"""

LIST_SELECTED_POLL_OPTIONS_SQL = """
SELECT option_key
FROM poll_selected_options
WHERE poll_id = ? AND telegram_user_id = ?
"""

DELETE_SELECTED_POLL_OPTIONS_SQL = """
DELETE FROM poll_selected_options
WHERE poll_id = ? AND telegram_user_id = ?
"""

INSERT_SELECTED_POLL_OPTION_SQL = """
INSERT INTO poll_selected_options (
    poll_id,
    telegram_user_id,
    option_key,
    selected_at
)
VALUES (?, ?, ?, ?)
"""

LIST_ACTIVE_USERS_WITH_SELECTED_OPTIONS_SQL = """
SELECT DISTINCT
    users.id,
    accounts.telegram_user_id,
    users.display_name,
    users.status,
    users.role,
    accounts.username,
    accounts.first_name,
    accounts.last_name
FROM poll_selected_options AS selections
JOIN telegram_accounts AS accounts
    ON accounts.telegram_user_id = selections.telegram_user_id
JOIN users ON users.id = accounts.user_id
WHERE selections.poll_id = ?
  AND users.status = ?
  AND selections.option_key IN ({option_placeholders})
ORDER BY users.display_name COLLATE NOCASE, users.id
"""
