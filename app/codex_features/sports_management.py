from flask import Blueprint, request, session
from app.shared.decorators import login_required
from .admin import admin_required, audit
from .helpers import APIError, body, choice, integer, lock_users, pagination, text_field, transaction
from .notifications import notify_meeting_members
from .waitlist import lock_schedule

sports_management_bp = Blueprint("sports_management", __name__, url_prefix="/api")


def lock_sports(cursor):
    cursor.execute("SELECT lock_name FROM feature_locks WHERE lock_name = 'sports' FOR UPDATE")
    if cursor.fetchone() is None:
        raise RuntimeError("Missing sports lock. Apply migration 010.")


def normalize_name(value):
    if not isinstance(value, str):
        raise APIError("sport_name must be a string.")
    value = " ".join(value.split())
    if not 1 <= len(value) <= 50:
        raise APIError("sport_name must contain 1 to 50 characters.")
    return value


@sports_management_bp.post("/sports/proposals")
@login_required
def propose_sport():
    name = normalize_name(body().get("sport_name"))
    user_id = session["user_id"]
    with transaction() as cursor:
        lock_sports(cursor)
        lock_users(cursor, user_id)
        cursor.execute("SELECT sport_id FROM sports WHERE sport_name = %s", (name,))
        if cursor.fetchone():
            raise APIError("Sport name already exists.", 409)
        cursor.execute("SELECT proposal_id FROM sport_proposals WHERE sport_name = %s", (name,))
        if cursor.fetchone():
            raise APIError("Sport name already proposed.", 409)
        cursor.execute("""SELECT COUNT(*) AS count FROM sport_proposals WHERE created_by = %s
            AND created_at >= UTC_DATE() AND created_at < UTC_DATE() + INTERVAL 1 DAY""", (user_id,))
        if cursor.fetchone()["count"] >= 5:
            raise APIError("Daily sport proposal limit reached.", 429)
        cursor.execute("INSERT INTO sport_proposals (sport_name,created_by,created_at) VALUES (%s,%s,UTC_TIMESTAMP())", (name, user_id))
        proposal_id = cursor.lastrowid
    return {"proposal_id": proposal_id, "status": "PENDING_REVIEW"}, 201


@sports_management_bp.get("/sports/proposals/mine")
@login_required
def my_proposals():
    with transaction() as cursor:
        cursor.execute("""SELECT proposal_id,sport_name,status,review_note,resolved_sport_id,created_at FROM sport_proposals
            WHERE created_by = %s ORDER BY proposal_id DESC LIMIT %s OFFSET %s""", (session["user_id"], *pagination()))
        return {"proposals": cursor.fetchall()}


@sports_management_bp.get("/admin/sports/proposals")
@admin_required
def proposals():
    status = request.args.get("status", "PENDING_REVIEW")
    if status:
        choice(status, ("PENDING_REVIEW", "APPROVED", "REJECTED", "MERGED"), "status")
    with transaction() as cursor:
        cursor.execute("""SELECT * FROM sport_proposals WHERE (%s = '' OR status = %s)
            ORDER BY proposal_id DESC LIMIT %s OFFSET %s""", (status, status, *pagination()))
        return {"proposals": cursor.fetchall()}


@sports_management_bp.get("/admin/sports")
@admin_required
def all_sports():
    with transaction() as cursor:
        cursor.execute("SELECT sport_id,sport_name,status,merged_into FROM sports ORDER BY sport_name LIMIT %s OFFSET %s", pagination())
        return {"sports": cursor.fetchall()}


def active_sport(cursor, sport_id):
    cursor.execute("SELECT sport_id FROM sports WHERE sport_id = %s AND status = 'ACTIVE' FOR UPDATE", (sport_id,))
    if not cursor.fetchone():
        raise APIError("Active sport not found.", 404)


@sports_management_bp.post("/admin/sports/proposals/<int:proposal_id>/<action>")
@admin_required
def review_proposal(proposal_id, action):
    choice(action, ("approve", "reject", "merge"), "action")
    data = body()
    note = text_field(data, "reason", 1, 1000)
    with transaction() as cursor:
        lock_sports(cursor)
        cursor.execute("SELECT * FROM sport_proposals WHERE proposal_id = %s FOR UPDATE", (proposal_id,))
        proposal = cursor.fetchone()
        if not proposal:
            raise APIError("Proposal not found.", 404)
        if proposal["status"] != "PENDING_REVIEW":
            raise APIError("Proposal already processed.", 409)
        resolved = None
        if action == "approve":
            cursor.execute("INSERT INTO sports (sport_name,created_by) VALUES (%s,%s)", (proposal["sport_name"], proposal["created_by"]))
            resolved = cursor.lastrowid
        elif action == "merge":
            resolved = integer(data.get("target_sport_id"), "target_sport_id")
            active_sport(cursor, resolved)
        status = {"approve": "APPROVED", "reject": "REJECTED", "merge": "MERGED"}[action]
        cursor.execute("""UPDATE sport_proposals SET status = %s, resolved_sport_id = %s,
            reviewed_by = %s, reviewed_at = UTC_TIMESTAMP(), review_note = %s WHERE proposal_id = %s""",
            (status, resolved, session["user_id"], note, proposal_id))
        audit(cursor, status, "SPORT_PROPOSAL", proposal_id, note)
    return {"status": status, "sport_id": resolved}


@sports_management_bp.post("/admin/sports/<int:sport_id>/merge")
@admin_required
def merge_sport(sport_id):
    data = body()
    target_id = integer(data.get("target_sport_id"), "target_sport_id")
    reason = text_field(data, "reason", 1, 1000)
    if target_id == sport_id:
        raise APIError("Cannot merge a sport into itself.", 409)
    with transaction() as cursor:
        lock_sports(cursor)
        lock_schedule(cursor)
        active_sport(cursor, sport_id)
        active_sport(cursor, target_id)
        cursor.execute("SELECT meeting_id FROM meetings WHERE sport_id = %s", (sport_id,))
        for meeting in cursor.fetchall():
            notify_meeting_members(cursor, meeting["meeting_id"])
        # Preserve a user's already selected target skill when both profiles exist.
        cursor.execute("""INSERT INTO user_sports (user_id,sport_id,skill_level)
            SELECT source.user_id,%s,source.skill_level FROM user_sports AS source WHERE source.sport_id = %s
            ON DUPLICATE KEY UPDATE skill_level = user_sports.skill_level""", (target_id, sport_id))
        cursor.execute("DELETE FROM user_sports WHERE sport_id = %s", (sport_id,))
        cursor.execute("UPDATE meetings SET sport_id = %s WHERE sport_id = %s", (target_id, sport_id))
        cursor.execute("UPDATE sport_proposals SET resolved_sport_id = %s WHERE resolved_sport_id = %s", (target_id, sport_id))
        cursor.execute("UPDATE sports SET status = 'INACTIVE', merged_into = %s WHERE sport_id = %s", (target_id, sport_id))
        audit(cursor, "MERGE", "SPORT", sport_id, reason)
    return {"message": "Sports merged.", "sport_id": target_id}
