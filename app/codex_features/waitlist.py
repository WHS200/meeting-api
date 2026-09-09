"""Meeting extensions executed inside existing participation/meeting transactions."""
from datetime import datetime
from flask import Blueprint, session
from app.shared.decorators import login_required
from .admin import check_active_user
from .helpers import APIError, lock_users, transaction
from .notifications import notify

waitlist_bp = Blueprint("waitlist", __name__, url_prefix="/api/meetings")


def lock_schedule(cursor):
    # A DB row lock works across threads/processes. Acquire before any meeting lock/read.
    # It serializes schedule-changing transactions, not message traffic or reads.
    cursor.execute("SELECT lock_name FROM feature_locks WHERE lock_name = 'schedule' FOR UPDATE")
    if cursor.fetchone() is None:
        raise RuntimeError("Missing schedule lock. Apply migration 009.")


def validate_duration(data):
    try:
        start = datetime.strptime(data["meeting_time"], "%H:%M")
        end = datetime.strptime(data.get("end_time", ""), "%H:%M")
    except (TypeError, ValueError, KeyError):
        return {"message": "end_time should be HH:MM."}, 400
    seconds = (end - start).total_seconds()
    if not 1800 <= seconds <= 43200:
        return {"message": "Meeting duration must be 30 minutes to 12 hours on the same date."}, 400
    return None


def has_overlap(cursor, user_id, meeting):
    cursor.execute("""SELECT m.meeting_id FROM meetings m
        LEFT JOIN meeting_participants mp ON mp.meeting_id = m.meeting_id
        WHERE (m.host_id = %s OR (mp.user_id = %s AND mp.participation_status = 'APPROVED'))
        AND m.status != 'CANCELED' AND m.meeting_id != %s
        AND m.meeting_date = %s AND m.meeting_time < %s AND %s < m.end_time
        LIMIT 1""", (user_id, user_id, meeting.get("meeting_id", 0), meeting["meeting_date"], meeting["end_time"], meeting["meeting_time"]))
    return cursor.fetchone() is not None


def ensure_no_overlap(cursor, user_id, meeting):
    lock_users(cursor, user_id)
    check_active_user(cursor, user_id)
    if has_overlap(cursor, user_id, meeting):
        raise APIError("An approved meeting overlaps this schedule.", 409)


def validate_meeting_update(cursor, meeting_id, data):
    cursor.execute("SELECT host_id FROM meetings WHERE meeting_id = %s", (meeting_id,))
    host = cursor.fetchone()
    user_ids = {host["host_id"]} if host else set()
    cursor.execute("SELECT user_id FROM meeting_participants WHERE meeting_id = %s AND participation_status = 'APPROVED'", (meeting_id,))
    members = cursor.fetchall()
    if len(members) + 1 > data["max_participants"]:
        raise APIError("Capacity cannot be smaller than current participants including host.", 409)
    if data["status"] != "CANCELED":
        proposed = dict(data, meeting_id=meeting_id)
        user_ids.update(member["user_id"] for member in members)
        for user_id in user_ids:
            if has_overlap(cursor, user_id, proposed):
                raise APIError("The new time conflicts with an approved participant's schedule.", 409)


def enqueue_waiter(cursor, meeting_id, user_id, from_pending=False):
    if from_pending:
        cursor.execute("""UPDATE meeting_participants SET participation_status = 'WAITING',
            waiting_at = CURRENT_TIMESTAMP(6) WHERE meeting_id = %s AND user_id = %s AND participation_status = 'PENDING'""", (meeting_id, user_id))
    else:
        cursor.execute("""INSERT INTO meeting_participants (meeting_id,user_id,participation_status,waiting_at)
            VALUES (%s,%s,'WAITING',CURRENT_TIMESTAMP(6))""", (meeting_id, user_id))


def promote_waiters(cursor, meeting):
    # Caller already owns schedule + meeting locks; member insert and notification are atomic.
    from app.participation_euna.helpers import add_chat_room_member
    if meeting["status"] not in ("RECRUITING", "CLOSED"):
        return []
    cursor.execute("SELECT COUNT(*) AS count FROM meeting_participants WHERE meeting_id = %s AND participation_status = 'APPROVED'", (meeting["meeting_id"],))
    places = meeting["max_participants"] - 1 - cursor.fetchone()["count"]
    if places <= 0:
        return []
    cursor.execute("""SELECT user_id FROM meeting_participants WHERE meeting_id = %s
        AND participation_status = 'WAITING' ORDER BY waiting_at, user_id""", (meeting["meeting_id"],))
    promoted = []
    for waiter in cursor.fetchall():
        user_id = waiter["user_id"]
        try:
            lock_users(cursor, user_id)
            check_active_user(cursor, user_id)
        except APIError as error:
            if error.status in (401,403,404):
                continue
            raise
        if has_overlap(cursor, user_id, meeting):
            continue
        cursor.execute("""UPDATE meeting_participants SET participation_status = 'APPROVED',
            approved_at = CURRENT_TIMESTAMP(), waiting_at = NULL
            WHERE meeting_id = %s AND user_id = %s AND participation_status = 'WAITING'""", (meeting["meeting_id"], user_id))
        add_chat_room_member(cursor, meeting["meeting_id"], user_id)
        notify(cursor, user_id, "WAITLIST_PROMOTED", "대기 중인 모임의 참여자로 승급되었습니다.", "MEETING", meeting["meeting_id"])
        promoted.append(user_id)
        if len(promoted) == places:
            break
    return promoted


@waitlist_bp.get("/<int:meeting_id>/waitlist")
@login_required
def list_waiters(meeting_id):
    with transaction() as cursor:
        cursor.execute("SELECT host_id FROM meetings WHERE meeting_id = %s", (meeting_id,))
        meeting = cursor.fetchone()
        if not meeting:
            raise APIError("Meeting not found.", 404)
        cursor.execute("""SELECT mp.user_id, mp.waiting_at, u.nickname
            FROM meeting_participants mp JOIN users u ON u.user_id = mp.user_id
            WHERE mp.meeting_id = %s AND mp.participation_status = 'WAITING'
            ORDER BY mp.waiting_at, mp.user_id""", (meeting_id,))
        rows = cursor.fetchall()
        ranked = [{**row, "position": position} for position, row in enumerate(rows, 1)]
        visible = ranked if meeting["host_id"] == session["user_id"] else [row for row in ranked if row["user_id"] == session["user_id"]]
        return {"waitlist": visible, "total": len(rows)}
