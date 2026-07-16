GET_TELEGRAM_DEBUG_ENABLED_SQL = """
SELECT enabled
FROM telegram_debug_settings
WHERE telegram_user_id = ?
"""

UPSERT_TELEGRAM_DEBUG_SQL = """
INSERT INTO telegram_debug_settings (
    telegram_user_id,
    enabled
)
VALUES (?, ?)
ON CONFLICT(telegram_user_id) DO UPDATE SET
    enabled = excluded.enabled,
    updated_at = CURRENT_TIMESTAMP
"""
