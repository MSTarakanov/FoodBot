GET_LUNCH_PINNED_MESSAGE_SQL = """
SELECT chat_id, message_id, lunch_date
FROM lunch_pinned_messages
WHERE chat_id = ?
"""

UPSERT_LUNCH_PINNED_MESSAGE_SQL = """
INSERT INTO lunch_pinned_messages (chat_id, message_id, lunch_date)
VALUES (?, ?, ?)
ON CONFLICT(chat_id) DO UPDATE SET
    message_id = excluded.message_id,
    lunch_date = excluded.lunch_date,
    updated_at = CURRENT_TIMESTAMP
"""

DELETE_LUNCH_PINNED_MESSAGE_SQL = """
DELETE FROM lunch_pinned_messages
WHERE chat_id = ?
"""
