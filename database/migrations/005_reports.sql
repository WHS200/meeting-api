CREATE TABLE reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_id INT NOT NULL,
    target_type ENUM('USER','MEETING','POST') NOT NULL,
    target_id INT NOT NULL,
    target_user_id INT NULL,
    target_meeting_id INT NULL,
    target_post_id INT NULL,
    reason VARCHAR(100) NOT NULL,
    detail VARCHAR(1000) NOT NULL DEFAULT '',
    status ENUM('OPEN','IN_REVIEW','RESOLVED','DISMISSED') NOT NULL DEFAULT 'OPEN',
    processed_by INT NULL,
    processed_at DATETIME NULL,
    process_note VARCHAR(1000) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(user_id),
    FOREIGN KEY (target_user_id) REFERENCES users(user_id),
    FOREIGN KEY (target_meeting_id) REFERENCES meetings(meeting_id) ON DELETE SET NULL,
    FOREIGN KEY (target_post_id) REFERENCES community_posts(post_id),
    FOREIGN KEY (processed_by) REFERENCES users(user_id),
    CHECK (target_id > 0),
    -- target_id preserves identity when a meeting's FK becomes NULL after deletion.
    CHECK (
        (target_type = 'USER' AND target_user_id = target_id AND target_user_id IS NOT NULL AND target_post_id IS NULL)
        OR (target_type = 'MEETING' AND target_user_id IS NULL AND target_post_id IS NULL)
        OR (target_type = 'POST' AND target_post_id = target_id AND target_post_id IS NOT NULL AND target_user_id IS NULL)
    ),
    INDEX idx_reporter_daily (reporter_id, created_at),
    INDEX idx_reporter_target (reporter_id, target_type, target_id, created_at),
    INDEX idx_reports_queue (status, target_type, report_id)
);
