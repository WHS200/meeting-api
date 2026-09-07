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
