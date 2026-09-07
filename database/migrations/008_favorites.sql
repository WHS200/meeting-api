CREATE TABLE meeting_favorites (
    user_id INT NOT NULL,
    meeting_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, meeting_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
    INDEX idx_favorites_user_created (user_id, created_at, meeting_id)
);
