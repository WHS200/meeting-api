ALTER TABLE users
    ADD COLUMN suspended_until DATETIME NULL,
    ADD COLUMN suspension_reason VARCHAR(1000) NULL,
    ADD INDEX idx_users_status (status, suspended_until);
ALTER TABLE meetings ADD COLUMN moderation_reason VARCHAR(1000) NULL;
CREATE TABLE admin_actions (
    action_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action VARCHAR(40) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    target_id INT NOT NULL,
    reason VARCHAR(1000) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(user_id),
    INDEX idx_actions_target (target_type, target_id, action_id)
);
