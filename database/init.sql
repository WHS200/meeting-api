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
    ('농구');