from flask import session

from app.shared.database import get_db_connection


# 모임 정보와 로그인 사용자 정보 가져오기
def get_meeting_context(meeting_id, for_update=False):
    user_id = session.get("user_id")

    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT *
            FROM meetings
            WHERE meeting_id = %s
        """
        if for_update:
            sql += " FOR UPDATE"

        cursor.execute(sql, (meeting_id,))

        meeting = cursor.fetchone()

    except Exception:
        if cursor is not None:
            cursor.close()
        connection.close()
        raise

    if meeting is None:
        cursor.close()
        connection.close()

        return None, None, None, None, (
            {"message": "Meeting Not Found"},
            404
        )

    return connection, cursor, meeting, user_id, None


# 모임 존재 여부와 모임장 권한 확인
def get_host_context(meeting_id, for_update=False):
    connection, cursor, meeting, user_id, error = get_meeting_context(
        meeting_id,
        for_update=for_update
    )

    if error:
        return None, None, None, None, error

    if meeting["host_id"] != user_id:
        cursor.close()
        connection.close()

        return None, None, None, None, (
            {"message": "Not Authorized"},
            403
        )

    return connection, cursor, meeting, user_id, None


def add_chat_room_member(cursor, meeting_id, user_id):
    cursor.execute(
        """
        SELECT chat_room_id
        FROM chat_rooms
        WHERE meeting_id = %s
        ORDER BY chat_room_id ASC
        LIMIT 1
        """,
        (meeting_id,)
    )
    chat_room = cursor.fetchone()

    if chat_room is None:
        raise RuntimeError("Meeting chat room not found.")

    cursor.execute(
        """
        INSERT IGNORE INTO chat_room_members (chat_room_id, user_id)
        VALUES (%s, %s)
        """,
        (chat_room["chat_room_id"], user_id)
    )


def remove_chat_room_member(cursor, meeting_id, user_id):
    cursor.execute(
        """
        DELETE FROM chat_room_members
        WHERE user_id = %s
        AND chat_room_id IN (
            SELECT chat_room_id
            FROM chat_rooms
            WHERE meeting_id = %s
        )
        """,
        (user_id, meeting_id)
    )

# 승인 대기 중인 참가 신청 상태 변경
def update_pending_status(cursor, meeting_id, target_user_id, status):

    # 승인 대기 중인 참가 신청인지 확인
    cursor.execute(
        """
        SELECT *
        FROM meeting_participants
        WHERE meeting_id = %s
        AND user_id = %s
        AND participation_status = 'PENDING'
        """,
        (meeting_id, target_user_id)
    )

    if cursor.fetchone() is None:
        return False

    # 승인 또는 거절 상태로 변경
    if status == "APPROVED":
        cursor.execute(
            """
            UPDATE meeting_participants
            SET participation_status = %s,
                approved_at = NOW()
            WHERE meeting_id = %s
            AND user_id = %s
            """,
            (status, meeting_id, target_user_id)
        )
    else:
        cursor.execute(
            """
            UPDATE meeting_participants
            SET participation_status = %s
            WHERE meeting_id = %s
            AND user_id = %s
            """,
            (status, meeting_id, target_user_id)
        )

    return True
