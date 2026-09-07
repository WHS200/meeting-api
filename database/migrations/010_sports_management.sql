-- Preflight normalized-name collisions before this UPDATE; UNIQUE rejects collisions.
UPDATE sports SET sport_name = REGEXP_REPLACE(TRIM(sport_name), '[[:space:]]+', ' ');
ALTER TABLE sports ADD COLUMN merged_into INT NULL,
    ADD CONSTRAINT fk_sports_merged_into FOREIGN KEY (merged_into) REFERENCES sports(sport_id);
CREATE TABLE sport_proposals (
    proposal_id INT AUTO_INCREMENT PRIMARY KEY,
    sport_name VARCHAR(50) NOT NULL UNIQUE,
    created_by INT NOT NULL,
    status ENUM('PENDING_REVIEW','APPROVED','REJECTED','MERGED') NOT NULL DEFAULT 'PENDING_REVIEW',
    resolved_sport_id INT NULL,
    reviewed_by INT NULL,
    reviewed_at DATETIME NULL,
    review_note VARCHAR(1000) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id),
    FOREIGN KEY (resolved_sport_id) REFERENCES sports(sport_id),
    CHECK (CHAR_LENGTH(sport_name) BETWEEN 1 AND 50),
    INDEX idx_sport_proposals_daily (created_by,created_at),
    INDEX idx_sport_proposals_review (status,proposal_id)
);
INSERT INTO feature_locks (lock_name) VALUES ('sports');
