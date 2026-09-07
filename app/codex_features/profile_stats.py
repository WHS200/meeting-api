from flask import Blueprint, session
from app.shared.decorators import login_required
from .helpers import APIError, transaction

profile_stats_bp = Blueprint("profile_stats", __name__, url_prefix="/api/users")


@profile_stats_bp.get("/me/stats")
@profile_stats_bp.get("/<int:user_id>/stats")
@login_required
def profile_stats(user_id=None):
    if user_id is None:
        user_id = session["user_id"]
    with transaction() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND status != 'DELETED'", (user_id,))
        if not cursor.fetchone():
            raise APIError("User not found.", 404)
        cursor.execute("""SELECT COUNT(*) AS participation_count,
            COALESCE(SUM(mp.attendance_status = 'ATTENDED'),0) AS attended_count,
            COALESCE(SUM(mp.attendance_status = 'NO_SHOW'),0) AS no_show_count
            FROM meeting_participants mp JOIN meetings m ON m.meeting_id = mp.meeting_id
            WHERE mp.user_id = %s AND mp.participation_status = 'APPROVED' AND m.status != 'CANCELED'""", (user_id,))
        stats = {key: int(value) for key, value in cursor.fetchone().items()}
        marked = stats["attended_count"] + stats["no_show_count"]
        stats["attendance_rate"] = round(stats["attended_count"] * 100 / marked, 1) if marked else None
        cursor.execute("SELECT COUNT(*) AS count FROM meetings WHERE host_id = %s", (user_id,))
        stats["hosted_count"] = cursor.fetchone()["count"]
        cursor.execute("""SELECT COUNT(*) AS count FROM friendships f JOIN users u
            ON u.user_id = CASE WHEN f.user_low = %s THEN f.user_high ELSE f.user_low END
            WHERE (f.user_low = %s OR f.user_high = %s) AND u.status != 'DELETED'""", (user_id, user_id, user_id))
        stats["friend_count"] = cursor.fetchone()["count"]
    return stats
