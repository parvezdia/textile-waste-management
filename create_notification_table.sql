-- Drop related tables if they exist (to avoid dependency issues)
DROP TABLE IF EXISTS notifications_notification CASCADE;

-- Create the notifications_notification table
CREATE TABLE notifications_notification (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    notification_type VARCHAR(10) NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES accounts_user(id) ON DELETE CASCADE
);

-- Create index for user_id for faster lookups
CREATE INDEX notifications_notification_user_id_idx ON notifications_notification(user_id);

-- Create index on created_at for sorting
CREATE INDEX notifications_notification_created_at_idx ON notifications_notification(created_at DESC);
