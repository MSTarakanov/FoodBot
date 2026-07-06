UPSERT_LUNCH_AUTO_CHAT_SQL = """
INSERT INTO lunch_auto_chats (chat_id, title, enabled)
VALUES (?, ?, 1)
ON CONFLICT(chat_id) DO UPDATE SET
    title = excluded.title,
    enabled = 1,
    updated_at = CURRENT_TIMESTAMP
"""

DISABLE_LUNCH_AUTO_CHAT_SQL = """
UPDATE lunch_auto_chats
SET enabled = 0,
    updated_at = CURRENT_TIMESTAMP
WHERE chat_id = ?
"""

GET_LUNCH_AUTO_CHAT_SQL = """
SELECT chat_id, title, enabled
FROM lunch_auto_chats
WHERE chat_id = ?
"""

LIST_ENABLED_LUNCH_AUTO_CHATS_SQL = """
SELECT chat_id, title, enabled
FROM lunch_auto_chats
WHERE enabled = 1
ORDER BY chat_id
"""
