from flask import Blueprint, session
from app.shared.decorators import login_required
from .helpers import APIError, body, choice, integer, lock_users, pagination, text_field, transaction

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")
TARGETS = {"USER": ("users", "user_id"), "MEETING": ("meetings", "meeting_id"), "POST": ("community_posts", "post_id")}


@reports_bp.post("")
@login_required
def create_report():
    data = body()
    target_type = choice(data.get("target_type"), TARGETS, "target_type")
    target_id = integer(data.get("target_id"), "target_id")
    reason = text_field(data, "reason", 1, 100)
    detail = text_field({"detail": data.get("detail", "")}, "detail", 0, 1000)
    reporter = session["user_id"]
    with transaction() as cursor:
        # Serializes daily and sliding-window limits for this reporter.
        lock_users(cursor, reporter)
        table, column = TARGETS[target_type]
        cursor.execute(f"SELECT * FROM {table} WHERE {column} = %s", (target_id,))
        target = cursor.fetchone()
        if not target or (target_type == "USER" and target["status"] == "DELETED") or (target_type == "POST" and target["deleted_at"]):
            raise APIError("Report target not found.", 404)
        if (target_type == "USER" and target_id == reporter) or (target_type == "POST" and target["author_id"] == reporter):
            raise APIError("Cannot report yourself or your post.", 409)
        cursor.execute("""SELECT COUNT(*) AS count FROM reports WHERE reporter_id = %s
            AND created_at >= CURRENT_DATE() AND created_at < CURRENT_DATE() + INTERVAL 1 DAY""", (reporter,))
        if cursor.fetchone()["count"] >= 10:
            raise APIError("Daily report limit reached.", 429)
        cursor.execute("""SELECT 1 FROM reports WHERE reporter_id = %s AND target_type = %s
            AND target_id = %s AND created_at > CURRENT_TIMESTAMP() - INTERVAL 24 HOUR LIMIT 1""",
            (reporter, target_type, target_id))
        if cursor.fetchone():
            raise APIError("Already reported this target within 24 hours.", 409)
        cursor.execute("""INSERT INTO reports (reporter_id, target_type, target_id,
            target_user_id, target_meeting_id, target_post_id, reason, detail, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP())""",
            (reporter, target_type, target_id, target_id if target_type == "USER" else None,
             target_id if target_type == "MEETING" else None, target_id if target_type == "POST" else None, reason, detail))
        report_id = cursor.lastrowid
    return {"report_id": report_id}, 201


@reports_bp.get("/mine")
@login_required
def my_reports():
    with transaction() as cursor:
        # Process notes may contain private moderation details; never expose them here.
        cursor.execute("""SELECT report_id, target_type, target_id, reason, detail, status, created_at, processed_at
            FROM reports WHERE reporter_id = %s ORDER BY report_id DESC LIMIT %s OFFSET %s""",
            (session["user_id"], *pagination()))
        return {"reports": cursor.fetchall()}
