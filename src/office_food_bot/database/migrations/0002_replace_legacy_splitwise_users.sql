DROP TABLE IF EXISTS splitwise_users_new;

CREATE TABLE splitwise_users_new (
    splitwise_user_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO splitwise_users_new (
    splitwise_user_id,
    user_id,
    email,
    updated_at
)
SELECT
    splitwise_user_id,
    user_id,
    '',
    updated_at
FROM splitwise_users;

DROP TABLE splitwise_users;

ALTER TABLE splitwise_users_new RENAME TO splitwise_users;
