GET_USER_VACATION_SQL = """
SELECT
    user_id,
    until_date
FROM user_vacations
WHERE user_id = ?
"""

UPSERT_USER_VACATION_SQL = """
INSERT INTO user_vacations (
    user_id,
    until_date
)
VALUES (?, ?)
ON CONFLICT(user_id) DO UPDATE SET
    until_date = excluded.until_date,
    updated_at = CURRENT_TIMESTAMP
"""

DELETE_USER_VACATION_SQL = """
DELETE FROM user_vacations
WHERE user_id = ?
"""

LIST_ACTIVE_VACATION_USER_IDS_SQL = """
SELECT user_id
FROM user_vacations
WHERE until_date >= ?
"""
