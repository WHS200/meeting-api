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
