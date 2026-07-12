CREATE_COFFEE_SESSION_SQL = """
INSERT INTO coffee_sessions (
    chat_id,
    initiator_user_id,
    last_proposer_user_id,
    scheduled_at,
    status
)
VALUES (?, ?, ?, ?, ?)
"""

GET_COFFEE_SESSION_SQL = """
SELECT * FROM coffee_sessions WHERE id = ?
"""

GET_OPEN_COFFEE_SESSION_SQL = """
SELECT *
FROM coffee_sessions
WHERE chat_id = ? AND status IN ('creating', 'active')
LIMIT 1
"""

LIST_RECOVERABLE_COFFEE_SESSIONS_SQL = """
SELECT *
FROM coffee_sessions
WHERE status IN ('creating', 'active', 'completing')
ORDER BY scheduled_at, id
"""

ACTIVATE_COFFEE_SESSION_SQL = """
UPDATE coffee_sessions
SET message_id = ?, status = 'active', updated_at = CURRENT_TIMESTAMP
WHERE id = ? AND status = 'creating'
"""

UPDATE_COFFEE_MESSAGE_SQL = """
UPDATE coffee_sessions
SET message_id = ?, updated_at = CURRENT_TIMESTAMP
WHERE id = ?
"""

RESCHEDULE_COFFEE_SESSION_SQL = """
UPDATE coffee_sessions
SET last_proposer_user_id = ?,
    scheduled_at = ?,
    notification_attempts = 0,
    next_attempt_at = NULL,
    retry_until = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ? AND status = 'active'
"""

INSERT_COFFEE_PARTICIPANT_SQL = """
INSERT INTO coffee_session_participants (session_id, user_id)
VALUES (?, ?)
ON CONFLICT(session_id, user_id) DO NOTHING
"""

DELETE_COFFEE_PARTICIPANT_SQL = """
DELETE FROM coffee_session_participants
WHERE session_id = ? AND user_id = ?
"""

LIST_COFFEE_PARTICIPANTS_SQL = """
SELECT
    users.id,
    accounts.telegram_user_id,
    users.display_name,
    users.status,
    users.role,
    accounts.username,
    accounts.first_name,
    accounts.last_name
FROM coffee_session_participants AS participants
JOIN users ON users.id = participants.user_id
JOIN telegram_accounts AS accounts ON accounts.user_id = users.id
WHERE participants.session_id = ?
ORDER BY participants.joined_at, users.id
"""

MARK_COFFEE_COMPLETING_SQL = """
UPDATE coffee_sessions
SET status = 'completing',
    notification_attempts = 0,
    next_attempt_at = NULL,
    retry_until = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ? AND status = 'active'
"""

MARK_COFFEE_RETRY_SQL = """
UPDATE coffee_sessions
SET status = 'completing',
    notification_attempts = ?,
    next_attempt_at = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ? AND status = 'completing'
"""

MARK_COFFEE_TERMINAL_SQL = """
UPDATE coffee_sessions
SET status = ?, next_attempt_at = NULL, completed_at = ?, updated_at = CURRENT_TIMESTAMP
WHERE id = ?
"""
