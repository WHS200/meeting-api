from flask import session

from app.shared.database import get_db_connection


# 로그인 여부와 모임 존재 여부를 공통으로 확인
def get_meeting_context(meeting_id):
    user_id = session.get("user_id")

    if user_id is None:
        return None, None, None, ({"message": "Login First"}, 401)

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

        return None, None, None, (
            {"message": "Meeting Not Found"},
            404
        )

    return connection, cursor, meeting, None


# 로그인, 모임 존재 여부와 함께 모임장 권한까지 확인
def get_host_context(meeting_id):
    connection, cursor, meeting, error = get_meeting_context(meeting_id)

    if error:
        return None, None, None, error

    user_id = session.get("user_id")

    if meeting["host_id"] != user_id:
        cursor.close()
        connection.close()

        return None, None, None, (
            {"message": "Not Authorized"},
            403
        )

    return connection, cursor, meeting, None
