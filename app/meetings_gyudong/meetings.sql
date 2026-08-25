CREATE TABLE meetings (
    meeting_id INT AUTO_INCREMENT PRIMARY KEY,
    host_id INT NOT NULL,
    sport_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    meeting_date DATE NOT NULL,
    meeting_time TIME NOT NULL,
    location VARCHAR(255) NOT NULL,
    max_participants INT NOT NULL,
    approval_type ENUM('INSTANT', 'APPROVAL') NOT NULL DEFAULT 'APPROVAL',
    status ENUM('RECRUITING', 'CLOSED', 'COMPLETED', 'CANCELED')
        NOT NULL DEFAULT 'RECRUITING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_meetings_max_participants CHECK (max_participants >= 2),
    CONSTRAINT fk_meetings_host
        FOREIGN KEY (host_id) REFERENCES users(user_id),
    CONSTRAINT fk_meetings_sport
        FOREIGN KEY (sport_id) REFERENCES sports(sport_id),
    INDEX idx_meetings_datetime (meeting_date, meeting_time),
    INDEX idx_meetings_sport_status (sport_id, status),
    INDEX idx_meetings_host (host_id)
);
