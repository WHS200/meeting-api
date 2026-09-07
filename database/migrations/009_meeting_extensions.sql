-- Preflight: meetings after 23:29:59 cannot receive a same-day >=30 minute backfill.
-- Inspect and correct those legacy rows BEFORE running this migration.
ALTER TABLE meetings ADD COLUMN end_time TIME NULL;
UPDATE meetings SET end_time = LEAST(ADDTIME(meeting_time, '01:00:00'), CAST('23:59:59' AS TIME));
ALTER TABLE meetings MODIFY COLUMN end_time TIME NOT NULL,
    ADD CONSTRAINT chk_meeting_duration CHECK (
        TIME_TO_SEC(end_time) - TIME_TO_SEC(meeting_time) BETWEEN 1800 AND 43200
        AND TIME_TO_SEC(meeting_time) >= 0 AND TIME_TO_SEC(end_time) < 86400
    );
ALTER TABLE meeting_participants
    MODIFY participation_status ENUM('PENDING','APPROVED','REJECTED','CANCELED','KICKED','WAITING') NOT NULL DEFAULT 'PENDING',
    ADD COLUMN waiting_at DATETIME(6) NULL,
    ADD INDEX idx_waitlist_order (meeting_id, participation_status, waiting_at, user_id),
    ADD INDEX idx_user_schedule (user_id, participation_status, meeting_id);
CREATE TABLE feature_locks (
    lock_name VARCHAR(40) PRIMARY KEY
);
INSERT INTO feature_locks (lock_name) VALUES ('schedule');
