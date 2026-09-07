CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    message VARCHAR(500) NOT NULL,
    target_type VARCHAR(20) NULL,
    target_id INT NULL,
    read_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_notifications_inbox (user_id, notification_id),
    INDEX idx_notifications_unread (user_id, read_at)
);
