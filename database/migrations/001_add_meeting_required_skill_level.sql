ALTER TABLE meetings
ADD COLUMN required_skill_level ENUM(
    'BRONZE',
    'SILVER',
    'GOLD',
    'MASTER'
) DEFAULT NULL
AFTER max_participants;
