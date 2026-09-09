"""ADMIN role checks and auditable moderation, independent of session login checks."""
from functools import wraps

from flask import Blueprint, request, session

from app.shared.decorators import login_required
from .helpers import (APIError, body, choice, integer, pagination, role_for,
                      serialize, text_field, transaction)
from .notifications import notify, notify_meeting_members

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def admin_required(function):
    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):
        with transaction() as cursor:
            if role_for(cursor, session["user_id"]) != "ADMIN":
                raise APIError("ADMIN role required.", 403)
        return function(*args, **kwargs)
    return wrapper


def check_active_user(cursor, user_id):
    cursor.execute("""SELECT status, (suspended_until IS NOT NULL AND suspended_until <= CURRENT_TIMESTAMP()) AS expired
        FROM users WHERE user_id = %s FOR UPDATE""", (user_id,))
    user = cursor.fetchone()
    if not user or user["status"] == "DELETED":
        raise APIError("User not found. Login again.", 401)
    if user["status"] == "SUSPENDED":
        if not user["expired"]:
            raise APIError("Account is suspended.", 403)
        cursor.execute("""UPDATE users SET status = 'ACTIVE', suspended_until = NULL
            WHERE user_id = %s AND status = 'SUSPENDED' AND suspended_until <= CURRENT_TIMESTAMP()""", (user_id,))


def socket_user_active(user_id):
    try:
        with transaction() as cursor:
            check_active_user(cursor, user_id)
        return True
    except APIError:
        return False


def audit(cursor, action, target_type, target_id, reason):
    cursor.execute("""INSERT INTO admin_actions (admin_id, action, target_type, target_id, reason, created_at)
        VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP())""", (session["user_id"], action, target_type, target_id, reason))


def suspend_user(cursor, user_id, days, reason):
    integer(days, "days", 1, 365)
    cursor.execute("SELECT user_id, role, status FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
    user = cursor.fetchone()
    if not user or user["status"] == "DELETED":
        raise APIError("User not found.", 404)
    if user["role"] == "ADMIN":
        raise APIError("ADMIN accounts cannot be suspended through this API.", 403)
    cursor.execute("""UPDATE users SET status = 'SUSPENDED', suspended_until = CURRENT_TIMESTAMP() + INTERVAL %s DAY,
        suspension_reason = %s WHERE user_id = %s""", (days, reason, user_id))
    audit(cursor, "SUSPEND", "USER", user_id, reason)


def cancel_meeting(cursor, meeting_id, reason):
    from .waitlist import lock_schedule
    lock_schedule(cursor)
    cursor.execute("SELECT status FROM meetings WHERE meeting_id = %s FOR UPDATE", (meeting_id,))
    row = cursor.fetchone()
    if not row:
        raise APIError("Meeting not found.", 404)
    if row["status"] == "CANCELED":
        raise APIError("Meeting already canceled.", 409)
    cursor.execute("UPDATE meetings SET status = 'CANCELED', moderation_reason = %s WHERE meeting_id = %s", (reason, meeting_id))
    audit(cursor, "CANCEL", "MEETING", meeting_id, reason)
    notify_meeting_members(cursor, meeting_id)


def remove_post(cursor, post_id, reason):
    cursor.execute("SELECT post_id FROM community_posts WHERE post_id = %s AND deleted_at IS NULL FOR UPDATE", (post_id,))
    if not cursor.fetchone():
        raise APIError("Post not found.", 404)
    cursor.execute("UPDATE community_posts SET deleted_at = CURRENT_TIMESTAMP() WHERE post_id = %s", (post_id,))
    audit(cursor, "DELETE", "POST", post_id, reason)


def evict_user(user_id):
    from app.chat_dahyun.socket_events import disconnect_user_sockets
    disconnect_user_sockets(user_id)


@admin_bp.get("/users")
@admin_required
def users():
    keyword = request.args.get("keyword", "")[:100]
    status = request.args.get("status", "")
    if status:
        choice(status, ("ACTIVE", "SUSPENDED", "DELETED"), "status")
    with transaction() as cursor:
        cursor.execute("""SELECT user_id, nickname, login_id, role, status, suspended_until, suspension_reason
            FROM users WHERE (%s = '' OR status = %s) AND (nickname LIKE %s OR login_id LIKE %s)
            ORDER BY user_id DESC LIMIT %s OFFSET %s""", (status, status, f"%{keyword}%", f"%{keyword}%", *pagination()))
        return {"users": cursor.fetchall()}


@admin_bp.get("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    with transaction() as cursor:
        cursor.execute("""SELECT user_id, nickname, login_id, email, region, role, status,
            suspended_until, suspension_reason, created_at FROM users WHERE user_id = %s""", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise APIError("User not found.", 404)
        cursor.execute("SELECT * FROM admin_actions WHERE target_type = 'USER' AND target_id = %s ORDER BY action_id DESC LIMIT 100", (user_id,))
        return {"user": user, "actions": cursor.fetchall()}


@admin_bp.post("/users/<int:user_id>/suspend")
@admin_required
def suspend(user_id):
    data = body()
    reason = text_field(data, "reason", 1, 1000)
    with transaction() as cursor:
        suspend_user(cursor, user_id, data.get("days"), reason)
    evict_user(user_id)
    return {"message": "User suspended."}


@admin_bp.post("/users/<int:user_id>/unsuspend")
@admin_required
def unsuspend(user_id):
    reason = text_field(body(), "reason", 1, 1000)
    with transaction() as cursor:
        cursor.execute("UPDATE users SET status = 'ACTIVE', suspended_until = NULL WHERE user_id = %s AND status = 'SUSPENDED'", (user_id,))
        if not cursor.rowcount:
            raise APIError("Suspended user not found.", 404)
        audit(cursor, "UNSUSPEND", "USER", user_id, reason)
    return {"message": "Suspension lifted."}


@admin_bp.get("/meetings")
@admin_required
def meetings():
    status = request.args.get("status", "")
    if status:
        choice(status, ("RECRUITING", "CLOSED", "COMPLETED", "CANCELED"), "status")
    keyword = request.args.get("keyword", "")[:100]
    with transaction() as cursor:
        cursor.execute("""SELECT meeting_id, host_id, title, meeting_date, meeting_time, status, moderation_reason
            FROM meetings WHERE (%s = '' OR status = %s) AND (title LIKE %s OR description LIKE %s)
            ORDER BY meeting_id DESC LIMIT %s OFFSET %s""", (status, status, f"%{keyword}%", f"%{keyword}%", *pagination()))
        return {"meetings": [serialize(row) for row in cursor.fetchall()]}


@admin_bp.post("/meetings/<int:meeting_id>/cancel")
@admin_required
def moderate_meeting(meeting_id):
    reason = text_field(body(), "reason", 1, 1000)
    with transaction() as cursor:
        cancel_meeting(cursor, meeting_id, reason)
    return {"message": "Meeting canceled."}


@admin_bp.get("/posts")
@admin_required
def posts():
    from .community import list_posts
    return list_posts()


@admin_bp.delete("/posts/<int:post_id>")
@admin_required
def moderate_post(post_id):
    reason = text_field(body(), "reason", 1, 1000)
    with transaction() as cursor:
        remove_post(cursor, post_id, reason)
    return "", 204


@admin_bp.post("/notices")
@admin_required
def notice():
    data = body()
    title, content = text_field(data, "title", 2, 100), text_field(data, "content", 1, 10000)
    with transaction() as cursor:
        cursor.execute("INSERT INTO community_posts (author_id, board, title, content) VALUES (%s,'NOTICE',%s,%s)", (session["user_id"], title, content))
        post_id = cursor.lastrowid
    return {"post_id": post_id}, 201


@admin_bp.get("/reports")
@admin_required
def reports():
    kind, status = request.args.get("target_type", ""), request.args.get("status", "")
    if kind:
        choice(kind, ("USER", "MEETING", "POST"), "target_type")
    if status:
        choice(status, ("OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED"), "status")
    with transaction() as cursor:
        cursor.execute("""SELECT report_id, target_type, target_id, reason, status, created_at FROM reports
            WHERE (%s = '' OR target_type = %s) AND (%s = '' OR status = %s)
            ORDER BY report_id DESC LIMIT %s OFFSET %s""", (kind, kind, status, status, *pagination()))
        return {"reports": cursor.fetchall()}


@admin_bp.get("/reports/<int:report_id>")
@admin_required
def report_detail(report_id):
    with transaction() as cursor:
        cursor.execute("SELECT * FROM reports WHERE report_id = %s", (report_id,))
        row = cursor.fetchone()
        if not row:
            raise APIError("Report not found.", 404)
        return {"report": row}


@admin_bp.patch("/reports/<int:report_id>")
@admin_required
def process_report(report_id):
    data = body()
    status = choice(data.get("status"), ("IN_REVIEW", "RESOLVED", "DISMISSED"), "status")
    note = text_field(data, "process_note", 1, 1000)
    action = choice(data.get("action", "NONE"), ("NONE", "DISMISS_REPORT", "SUSPEND_USER", "CANCEL_MEETING", "DELETE_POST"), "action")
    if action == "DISMISS_REPORT":
        status = "DISMISSED"
    elif action in ("SUSPEND_USER", "CANCEL_MEETING", "DELETE_POST"):
        status = "RESOLVED"
    if action != "NONE" and status != "RESOLVED":
        raise APIError("A moderation action requires RESOLVED status.")
    suspended_id = None
    with transaction() as cursor:
        cursor.execute("SELECT * FROM reports WHERE report_id = %s FOR UPDATE", (report_id,))
        row = cursor.fetchone()
        if not row:
            raise APIError("Report not found.", 404)
        if row["status"] in ("RESOLVED", "DISMISSED"):
            raise APIError("Report already completed.", 409)
        if action != "NONE":
            expected = {"SUSPEND_USER": "USER", "CANCEL_MEETING": "MEETING", "DELETE_POST": "POST"}.get(action)
            if expected and row["target_type"] != expected:
                raise APIError("Action does not match report target.")
            # Only the target stored in the report can be acted on. Ignore caller-supplied IDs.
            target_id = row["target_id"]
            if action == "DISMISS_REPORT":
                pass
            elif action == "SUSPEND_USER":
                suspend_user(cursor, target_id, data.get("days"), note)
                suspended_id = target_id
            elif action == "CANCEL_MEETING":
                cancel_meeting(cursor, target_id, note)
            else:
                remove_post(cursor, target_id, note)
        cursor.execute("""UPDATE reports SET status = %s, processed_by = %s,
            processed_at = CURRENT_TIMESTAMP(), process_note = %s WHERE report_id = %s""",
            (status, session["user_id"], note, report_id))
        audit(cursor, status, "REPORT", report_id, note)
        if status in ("RESOLVED", "DISMISSED"):
            notify(cursor, row["reporter_id"], "REPORT_PROCESSED", "접수한 신고의 처리가 완료되었습니다.", "REPORT", report_id)
    if suspended_id:
        evict_user(suspended_id)
    return {"message": "Report processed.", "status": status}
