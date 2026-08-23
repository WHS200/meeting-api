from flask import session

from app.shared.database import get_db_connection


# 로그인 여부와 모임 존재 여부를 공통으로 확인
def get_meeting_context(meeting_id):
    user_id = session.get("user_id")

    if user_id is None:
        return None, None, None, None, (
            {"message": "Login First"},
            401
        )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM meetings
        WHERE meeting_id = %s
        """,
        (meeting_id,)
    )

    meeting = cursor.fetchone()

    if meeting is None:
        cursor.close()
        connection.close()

        return None, None, None, None, (
            {"message": "Meeting Not Found"},
            404
        )

    return connection, cursor, meeting, user_id, None


# 로그인, 모임 존재 여부와 함께 모임장 권한까지 확인
def get_host_context(meeting_id):
    connection, cursor, meeting, user_id, error = get_meeting_context(meeting_id)

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
