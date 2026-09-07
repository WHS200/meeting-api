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
