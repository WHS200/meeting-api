from flask import Blueprint, request

from app.participation_euna.helpers import (
    get_meeting_context,
    get_host_context,
    update_pending_status
)


participation_bp = Blueprint(
    "participation",
    __name__,
    url_prefix="/api/meetings"
)

# 모임 참여 신청
@participation_bp.post("/<int:meeting_id>/participants")
def join_meeting(meeting_id):

    # 로그인 여부와 모임 존재 여부 확인
    connection, cursor, meeting, user_id, error = get_meeting_context(meeting_id)

    if error:
        return error

    # 이미 참여 신청한 사용자인지 확인
    cursor.execute(
        """
        SELECT *
        FROM meeting_participants
        WHERE meeting_id = %s
        AND user_id = %s
        """,
        (meeting_id, user_id)
    )

    participant = cursor.fetchone()

    if participant:
        cursor.close()
        connection.close()
        return {"message": "Already Participated"}, 409

    # 현재 승인된 참여자 수 확인
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM meeting_participants
        WHERE meeting_id = %s
        AND participation_status = 'APPROVED'
        """,
        (meeting_id,)
    )

    participant_count = cursor.fetchone()["count"]

    # 정원 초과 여부 확인
    if participant_count >= meeting["max_participants"]:
        cursor.close()
        connection.close()
        return {"message": "Meeting Full"}, 409

    # 승인 방식에 따라 참여 상태 결정
    if meeting["approval_type"] == "INSTANT":
        participation_status = "APPROVED"
    else:
        participation_status = "PENDING"

    # 참여 정보 저장
    cursor.execute(
        """
        INSERT INTO meeting_participants
            (meeting_id, user_id, participation_status)
        VALUES (%s, %s, %s)
        """,
        (meeting_id, user_id, participation_status)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Participation Successful",
        "participation_status": participation_status
    }, 201

# 내 참여 신청 취소
@participation_bp.delete("/<int:meeting_id>/participants/me")
def cancel_participation(meeting_id):

    # 로그인 여부와 모임 존재 여부 확인
    connection, cursor, meeting, user_id, error = get_meeting_context(meeting_id)

    if error:
        return error

    # 내 참여 기록 확인
    cursor.execute(
        """
        SELECT *
        FROM meeting_participants
        WHERE meeting_id = %s
        AND user_id = %s
        """,
        (meeting_id, user_id)
    )

    participant = cursor.fetchone()

    if participant is None:
        cursor.close()
        connection.close()
        return {"message": "Participation Not Found"}, 404

    # 참여 상태를 취소로 변경
    cursor.execute(
        """
        UPDATE meeting_participants
        SET participation_status = 'CANCELED',
            canceled_at = NOW()
        WHERE meeting_id = %s
        AND user_id = %s
        """,
        (meeting_id, user_id)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Participation Canceled"}, 200

# 참가 신청 목록 조회
@participation_bp.get("/<int:meeting_id>/participants")
def get_pending_participants(meeting_id):

    # 로그인, 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    # 승인 대기 중인 참가 신청 목록 조회
    cursor.execute(
        """
        SELECT
            mp.user_id,
            u.nickname,
            mp.participation_status
        FROM meeting_participants mp
        JOIN users u ON mp.user_id = u.user_id
        WHERE mp.meeting_id = %s
        AND mp.participation_status = 'PENDING'
        """,
        (meeting_id,)
    )

    participants = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "participants": participants
    }, 200

# 참가 신청 승인
@participation_bp.post(
    "/<int:meeting_id>/participants/<int:target_user_id>/approve"
)
def approve_participant(meeting_id, target_user_id):

    # 로그인, 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    # 승인 대기 중인 참가 신청을 APPROVED 상태로 변경
    if not update_pending_status(
        cursor, meeting_id, target_user_id, "APPROVED"
    ):
        cursor.close()
        connection.close()
        return {"message": "Pending Participation Not Found"}, 404

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Participation Approved"}, 200

# 참가 신청 거절
@participation_bp.post(
    "/<int:meeting_id>/participants/<int:target_user_id>/reject"
)
def reject_participant(meeting_id, target_user_id):

    # 로그인, 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    # 승인 대기 중인 참가 신청을 REJECTED 상태로 변경
    if not update_pending_status(
        cursor, meeting_id, target_user_id, "REJECTED"
    ):
        cursor.close()
        connection.close()
        return {"message": "Pending Participation Not Found"}, 404

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Participation Rejected"}, 200

# 현재 참여자 목록 조회
@participation_bp.get("/<int:meeting_id>/participants/approved")
def get_approved_participants(meeting_id):

    # 로그인 여부와 모임 존재 여부 확인
    connection, cursor, meeting, user_id, error = get_meeting_context(meeting_id)

    if error:
        return error

    # 승인된 참여자 목록 조회
    cursor.execute(
        """
        SELECT *
        FROM meeting_participants
        WHERE meeting_id = %s
        AND participation_status = 'APPROVED'
        """,
        (meeting_id,)
    )

    participants = cursor.fetchall()

    cursor.close()
    connection.close()

    return {
        "participants": participants
    }, 200

# 참여자 강퇴
@participation_bp.delete(
    "/<int:meeting_id>/participants/<int:target_user_id>"
)
def kick_participant(meeting_id, target_user_id):

    # 로그인, 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    # 강퇴 대상이 현재 승인된 참여자인지 확인
    cursor.execute(
        """
        SELECT *
        FROM meeting_participants
        WHERE meeting_id = %s
        AND user_id = %s
        AND participation_status = 'APPROVED'
        """,
        (meeting_id, target_user_id)
    )

    participant = cursor.fetchone()

    if participant is None:
        cursor.close()
        connection.close()
        return {"message": "Participant Not Found"}, 404

    # 참여 상태를 강퇴로 변경
    cursor.execute(
        """
        UPDATE meeting_participants
        SET participation_status = 'KICKED'
        WHERE meeting_id = %s
        AND user_id = %s
        """,
        (meeting_id, target_user_id)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Participant Kicked"}, 200

# 출석 / No-Show 처리
@participation_bp.post(
    "/<int:meeting_id>/participants/<int:target_user_id>/attendance"
)
def update_attendance(meeting_id, target_user_id):

    # 로그인, 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    # 출석 처리 대상이 현재 승인된 참여자인지 확인
    cursor.execute(
        """
        SELECT *
        FROM meeting_participants
        WHERE meeting_id = %s
        AND user_id = %s
        AND participation_status = 'APPROVED'
        """,
        (meeting_id, target_user_id)
    )

    participant = cursor.fetchone()

    if participant is None:
        cursor.close()
        connection.close()
        return {"message": "Participant Not Found"}, 404

    # 요청으로 받은 출석 상태 확인
    data = request.get_json()
    attendance_status = data.get("attendance_status")

    if attendance_status not in ["ATTENDED", "NO_SHOW"]:
        cursor.close()
        connection.close()
        return {"message": "Invalid Attendance Status"}, 400

    # 출석 상태 저장
    cursor.execute(
        """
        UPDATE meeting_participants
        SET attendance_status = %s
        WHERE meeting_id = %s
        AND user_id = %s
        """,
        (attendance_status, meeting_id, target_user_id)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Attendance Updated"}, 200

