from flask import Blueprint, session
from app.shared.decorators import login_required
from .helpers import APIError, pagination, transaction

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def notify(cursor, user_id, event_type, message, target_type=None, target_id=None):
    """Always use the caller's cursor: domain change and notification commit together."""
    cursor.execute("""INSERT INTO notifications (user_id, event_type, message, target_type, target_id, created_at)
        VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())""", (user_id, event_type, message, target_type, target_id))


def notify_meeting_members(cursor, meeting_id):
    cursor.execute("""SELECT user_id FROM meeting_participants WHERE meeting_id = %s
        AND participation_status IN ('APPROVED','PENDING','WAITING')""", (meeting_id,))
    for member in cursor.fetchall():
        if member["user_id"] != session.get("user_id"):
            notify(cursor, member["user_id"], "MEETING_CHANGED", "모임의 주요 정보가 변경되었습니다.", "MEETING", meeting_id)


def notify_meeting_changes(cursor, meeting_id, data):
    # Called before UPDATE inside its transaction. Compare normalized date/time strings.
    from .helpers import serialize
    cursor.execute("SELECT * FROM meetings WHERE meeting_id = %s", (meeting_id,))
    old = serialize(cursor.fetchone())
    if not old:
        return
    changed = False
    for key in ("title", "description", "meeting_date", "meeting_time", "end_time", "location", "sport_id", "max_participants", "status"):
        if key not in data:
            continue
        first, second = old.get(key), data[key]
        if key in ("meeting_time", "end_time"):
            first, second = str(first)[:5], str(second)[:5]
        if first != second:
            changed = True
    if changed:
        notify_meeting_members(cursor, meeting_id)


@notifications_bp.get("")
@login_required
def list_notifications():
    with transaction() as cursor:
        cursor.execute("""SELECT notification_id, event_type, message, target_type, target_id, created_at, read_at
            FROM notifications WHERE user_id = %s ORDER BY notification_id DESC LIMIT %s OFFSET %s""",
            (session["user_id"], *pagination()))
        return {"notifications": cursor.fetchall()}


@notifications_bp.get("/unread-count")
@login_required
def unread_count():
    with transaction() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM notifications WHERE user_id = %s AND read_at IS NULL", (session["user_id"],))
        return cursor.fetchone()


@notifications_bp.post("/<int:notification_id>/read")
@login_required
def read_notification(notification_id):
    with transaction() as cursor:
        cursor.execute("SELECT notification_id FROM notifications WHERE notification_id = %s AND user_id = %s FOR UPDATE", (notification_id, session["user_id"]))
        if not cursor.fetchone():
            raise APIError("Notification not found.", 404)
        cursor.execute("""UPDATE notifications SET read_at = COALESCE(read_at, UTC_TIMESTAMP())
            WHERE notification_id = %s AND user_id = %s""", (notification_id, session["user_id"]))
    return {"message": "Notification read."}


@notifications_bp.post("/read-all")
@login_required
def read_all():
    with transaction() as cursor:
        cursor.execute("UPDATE notifications SET read_at = UTC_TIMESTAMP() WHERE user_id = %s AND read_at IS NULL", (session["user_id"],))
    return {"message": "All notifications read."}
