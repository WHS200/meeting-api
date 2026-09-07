SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- =========================================
-- USERS
-- =========================================

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,

    password VARCHAR(255) NOT NULL,
    login_id VARCHAR(50) UNIQUE NOT NULL,
    nickname VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,

    profile_image VARCHAR(500),

    birth_date DATE NOT NULL,
    gender ENUM('MALE', 'FEMALE') NOT NULL,
    region VARCHAR(50) NOT NULL,

    role ENUM('USER', 'ADMIN')
        NOT NULL DEFAULT 'USER',

    status ENUM('ACTIVE', 'SUSPENDED', 'DELETED')
        NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);


-- =========================================
-- SPORTS
-- =========================================

CREATE TABLE sports (
    sport_id INT AUTO_INCREMENT PRIMARY KEY,

    sport_name VARCHAR(50) UNIQUE NOT NULL,

    created_by INT,

    status ENUM('ACTIVE', 'INACTIVE')
        NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sports_created_by
        FOREIGN KEY (created_by)
        REFERENCES users(user_id)
);


-- =========================================
-- USER_SPORTS
-- =========================================

CREATE TABLE user_sports (
    user_id INT NOT NULL,
    sport_id INT NOT NULL,

    skill_level ENUM(
        'BRONZE',
        'SILVER',
        'GOLD',
        'MASTER'
    ) NOT NULL,

    PRIMARY KEY (user_id, sport_id),

    CONSTRAINT fk_user_sports_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_user_sports_sport
        FOREIGN KEY (sport_id)
        REFERENCES sports(sport_id)
);


-- =========================================
-- MEETINGS
-- =========================================

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

    required_skill_level ENUM(
        'BRONZE',
        'SILVER',
        'GOLD',
        'MASTER'
    ) DEFAULT NULL,

    approval_type ENUM(
        'INSTANT',
        'APPROVAL'
    ) NOT NULL DEFAULT 'APPROVAL',

    status ENUM(
        'RECRUITING',
        'CLOSED',
        'COMPLETED',
        'CANCELED'
    ) NOT NULL DEFAULT 'RECRUITING',

    created_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_meetings_max_participants
        CHECK (max_participants >= 2),

    CONSTRAINT fk_meetings_host
        FOREIGN KEY (host_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_meetings_sport
        FOREIGN KEY (sport_id)
        REFERENCES sports(sport_id),

    INDEX idx_meetings_date (meeting_date),
    INDEX idx_meetings_sport_status (sport_id, status),
    INDEX idx_meetings_host (host_id)
);


-- =========================================
-- MEETING_PARTICIPANTS
-- =========================================

CREATE TABLE meeting_participants (
    meeting_id INT NOT NULL,
    user_id INT NOT NULL,

    participation_status ENUM(
        'PENDING',
        'APPROVED',
        'REJECTED',
        'CANCELED',
        'KICKED'
    ) NOT NULL DEFAULT 'PENDING',

    attendance_status ENUM(
        'ATTENDED',
        'NO_SHOW'
    ) DEFAULT NULL,

    applied_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    approved_at DATETIME DEFAULT NULL,
    canceled_at DATETIME DEFAULT NULL,

    PRIMARY KEY (meeting_id, user_id),

    CONSTRAINT fk_participants_meeting
        FOREIGN KEY (meeting_id)
        REFERENCES meetings(meeting_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_participants_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    INDEX idx_participants_status (
        meeting_id,
        participation_status
    )
);


-- =========================================
-- CHAT_ROOMS
-- =========================================

CREATE TABLE chat_rooms (
    chat_room_id INT AUTO_INCREMENT PRIMARY KEY,

    room_type VARCHAR(20) NOT NULL,

    meeting_id INT,

    created_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_rooms_meeting
        FOREIGN KEY (meeting_id)
        REFERENCES meetings(meeting_id)
        ON DELETE CASCADE
);


-- =========================================
-- CHAT_ROOM_MEMBERS
-- =========================================

CREATE TABLE chat_room_members (
    chat_room_id INT NOT NULL,
    user_id INT NOT NULL,
    
    joined_at DATETIME
	    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (chat_room_id, user_id),

    CONSTRAINT fk_chat_room_members_room
        FOREIGN KEY (chat_room_id)
        REFERENCES chat_rooms(chat_room_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_chat_room_members_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id),

    INDEX idx_chat_room_members_user (user_id)
);


-- =========================================
-- CHAT_MESSAGES
-- =========================================

CREATE TABLE chat_messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,

    chat_room_id INT NOT NULL,
    sender_id INT NOT NULL,

    content TEXT NOT NULL,

    created_at DATETIME
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_messages_room
        FOREIGN KEY (chat_room_id)
        REFERENCES chat_rooms(chat_room_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_chat_messages_sender
        FOREIGN KEY (sender_id)
        REFERENCES users(user_id),

    INDEX idx_chat_messages_room_created (
        chat_room_id,
        created_at
    )
);

INSERT IGNORE INTO sports (sport_name)
VALUES
    ('탁구'),
    ('배드민턴'),
    ('테니스'),
    ('풋살'),
    ('농구'),
    ('런닝');
-- Apply after 001. MySQL >= 8.0.16. UTC timestamps.
CREATE TABLE friend_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    recipient_id INT NOT NULL,
    status ENUM('PENDING','ACCEPTED','REJECTED','CANCELED') NOT NULL DEFAULT 'PENDING',
    pending_low INT GENERATED ALWAYS AS (IF(status = 'PENDING', LEAST(sender_id, recipient_id), NULL)) STORED,
    pending_high INT GENERATED ALWAYS AS (IF(status = 'PENDING', GREATEST(sender_id, recipient_id), NULL)) STORED,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (sender_id <> recipient_id),
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (recipient_id) REFERENCES users(user_id),
    UNIQUE KEY uq_pending_friend_pair (pending_low, pending_high),
    INDEX idx_requests_recipient (recipient_id, status, request_id),
    INDEX idx_requests_sender (sender_id, status, request_id)
);
CREATE TABLE friendships (
    user_low INT NOT NULL,
    user_high INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_low, user_high),
    CHECK (user_low < user_high),
    FOREIGN KEY (user_low) REFERENCES users(user_id),
    FOREIGN KEY (user_high) REFERENCES users(user_id),
    INDEX idx_friends_high (user_high)
);
CREATE TABLE user_blocks (
    blocker_id INT NOT NULL,
    blocked_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id),
    FOREIGN KEY (blocker_id) REFERENCES users(user_id),
    FOREIGN KEY (blocked_id) REFERENCES users(user_id),
    INDEX idx_blocked_user (blocked_id)
);
ALTER TABLE chat_rooms
    ADD COLUMN direct_low INT NULL,
    ADD COLUMN direct_high INT NULL,
    ADD CONSTRAINT fk_direct_low FOREIGN KEY (direct_low) REFERENCES users(user_id),
    ADD CONSTRAINT fk_direct_high FOREIGN KEY (direct_high) REFERENCES users(user_id),
    ADD UNIQUE KEY uq_direct_pair (direct_low, direct_high),
    ADD CONSTRAINT chk_direct_pair CHECK (
        (room_type = 'DIRECT' AND meeting_id IS NULL AND direct_low IS NOT NULL
         AND direct_high IS NOT NULL AND direct_low < direct_high)
        OR (room_type <> 'DIRECT' AND direct_low IS NULL AND direct_high IS NULL)
    );
CREATE TABLE community_posts (
    post_id INT AUTO_INCREMENT PRIMARY KEY,
    author_id INT NOT NULL,
    board ENUM('FREE','TIPS','NOTICE') NOT NULL,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    FOREIGN KEY (author_id) REFERENCES users(user_id),
    CHECK (CHAR_LENGTH(title) BETWEEN 2 AND 100),
    CHECK (CHAR_LENGTH(content) BETWEEN 1 AND 10000),
    INDEX idx_posts_board (board, deleted_at, post_id),
    INDEX idx_posts_author (author_id, post_id)
);
CREATE TABLE community_comments (
    comment_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    author_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id),
    FOREIGN KEY (author_id) REFERENCES users(user_id),
    CHECK (CHAR_LENGTH(content) BETWEEN 1 AND 1000),
    INDEX idx_comments_post (post_id, deleted_at, comment_id)
);
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
CREATE TABLE meeting_favorites (
    user_id INT NOT NULL,
    meeting_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, meeting_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE,
    INDEX idx_favorites_user_created (user_id, created_at, meeting_id)
);
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
