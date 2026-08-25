from flask import Blueprint, request

from app.shared.decorators import login_required
from app.participation_euna.helpers import (
    add_chat_room_member,
    get_meeting_context,
    get_host_context,
    remove_chat_room_member,
    update_pending_status
)


participation_bp = Blueprint(
    "participation",
    __name__,
    url_prefix="/api/meetings"
)

# 모임 참여 신청
@participation_bp.post("/<int:meeting_id>/participants")
@login_required
def join_meeting(meeting_id):

    # 모임 존재 여부 확인
    connection, cursor, meeting, user_id, error = get_meeting_context(
        meeting_id,
        for_update=True
    )

    if error:
        return error

    try:
        if meeting["status"] != "RECRUITING":
            return {"message": "Meeting is not recruiting."}, 409

        if meeting["host_id"] == user_id:
            return {"message": "Host cannot participate in own meeting."}, 409

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
        if participant_count + 1 >= meeting["max_participants"]:
            return {"message": "Meeting Full"}, 409

        # 승인 방식에 따라 참여 상태 결정
        if meeting["approval_type"] == "INSTANT":
            participation_status = "APPROVED"

            cursor.execute(
                """
                INSERT INTO meeting_participants
                    (meeting_id, user_id, participation_status, approved_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (meeting_id, user_id, participation_status)
            )
            add_chat_room_member(cursor, meeting_id, user_id)
        else:
            participation_status = "PENDING"

            cursor.execute(
                """
                INSERT INTO meeting_participants
                    (meeting_id, user_id, participation_status)
                VALUES (%s, %s, %s)
                """,
                (meeting_id, user_id, participation_status)
            )

        connection.commit()

        return {
            "message": "Participation Successful",
            "participation_status": participation_status
        }, 201

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

# 내 참여 신청 취소
@participation_bp.delete("/<int:meeting_id>/participants/me")
@login_required
def cancel_participation(meeting_id):

    # 모임 존재 여부 확인
    connection, cursor, meeting, user_id, error = get_meeting_context(meeting_id)

    if error:
        return error

    try:
        # 내 참여 기록 확인
        cursor.execute(
            """
            SELECT *
            FROM meeting_participants
            WHERE meeting_id = %s
            AND user_id = %s
            AND participation_status IN ('PENDING', 'APPROVED')
            """,
            (meeting_id, user_id)
        )

        participant = cursor.fetchone()

        if participant is None:
            return {"message": "Participation Not Found"}, 404

        # 참여 상태를 취소로 변경
        cursor.execute(
            """
            UPDATE meeting_participants
            SET participation_status = 'CANCELED',
                canceled_at = NOW()
            WHERE meeting_id = %s
            AND user_id = %s
            AND participation_status IN ('PENDING', 'APPROVED')
            """,
            (meeting_id, user_id)
        )

        remove_chat_room_member(cursor, meeting_id, user_id)

        connection.commit()

        return {"message": "Participation Canceled"}, 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

# 참가 신청 목록 조회
@participation_bp.get("/<int:meeting_id>/participants")
@login_required
def get_pending_participants(meeting_id):

    # 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    try:
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

        return {
            "participants": participants
        }, 200

    finally:
        cursor.close()
        connection.close()

# 참가 신청 승인
@participation_bp.post(
    "/<int:meeting_id>/participants/<int:target_user_id>/approve"
)
@login_required
def approve_participant(meeting_id, target_user_id):

    # 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(
        meeting_id,
        for_update=True
    )

    if error:
        return error

    try:
        if meeting["status"] != "RECRUITING":
            return {"message": "Meeting is not recruiting."}, 409

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
        if participant_count + 1 >= meeting["max_participants"]:
            return {"message": "Meeting Full"}, 409

        # 승인 대기 중인 참가 신청을 APPROVED 상태로 변경
        if not update_pending_status(
            cursor, meeting_id, target_user_id, "APPROVED"
        ):
            return {"message": "Pending Participation Not Found"}, 404

        add_chat_room_member(cursor, meeting_id, target_user_id)

        connection.commit()

        return {"message": "Participation Approved"}, 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

# 참가 신청 거절
@participation_bp.post(
    "/<int:meeting_id>/participants/<int:target_user_id>/reject"
)
@login_required
def reject_participant(meeting_id, target_user_id):

    # 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    try:
        # 승인 대기 중인 참가 신청을 REJECTED 상태로 변경
        if not update_pending_status(
            cursor, meeting_id, target_user_id, "REJECTED"
        ):
            return {"message": "Pending Participation Not Found"}, 404

        connection.commit()

        return {"message": "Participation Rejected"}, 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

# 현재 참여자 목록 조회
@participation_bp.get("/<int:meeting_id>/participants/approved")
@login_required
def get_approved_participants(meeting_id):

    # 모임 존재 여부 확인
    connection, cursor, meeting, user_id, error = get_meeting_context(meeting_id)

    if error:
        return error

    try:
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

        return {
            "participants": participants
        }, 200

    finally:
        cursor.close()
        connection.close()

# 참여자 강퇴
@participation_bp.delete(
    "/<int:meeting_id>/participants/<int:target_user_id>"
)
@login_required
def kick_participant(meeting_id, target_user_id):

    # 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    try:
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

        remove_chat_room_member(cursor, meeting_id, target_user_id)

        connection.commit()

        return {"message": "Participant Kicked"}, 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

# 출석 / No-Show 처리
@participation_bp.post(
    "/<int:meeting_id>/participants/<int:target_user_id>/attendance"
)
@login_required
def update_attendance(meeting_id, target_user_id):

    # 모임 존재 여부와 모임장 권한 확인
    connection, cursor, meeting, user_id, error = get_host_context(meeting_id)

    if error:
        return error

    try:
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
            return {"message": "Participant Not Found"}, 404

        # 요청으로 받은 출석 상태 확인
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return {"message": "Invalid Request"}, 400

        attendance_status = data.get("attendance_status")

        if attendance_status not in ["ATTENDED", "NO_SHOW"]:
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

        return {"message": "Attendance Updated"}, 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

