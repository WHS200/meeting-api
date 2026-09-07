from flask import Blueprint, session
from app.shared.decorators import login_required
from .helpers import APIError, pagination, serialize, transaction

favorites_bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")


@favorites_bp.post("/<int:meeting_id>")
@login_required
def add_favorite(meeting_id):
    with transaction() as cursor:
        cursor.execute("SELECT meeting_id FROM meetings WHERE meeting_id = %s FOR UPDATE", (meeting_id,))
        if not cursor.fetchone():
            raise APIError("Meeting not found.", 404)
        cursor.execute("INSERT INTO meeting_favorites (user_id, meeting_id) VALUES (%s,%s)", (session["user_id"], meeting_id))
    return {"message": "Meeting saved."}, 201


@favorites_bp.delete("/<int:meeting_id>")
@login_required
def remove_favorite(meeting_id):
    with transaction() as cursor:
        cursor.execute("DELETE FROM meeting_favorites WHERE user_id = %s AND meeting_id = %s", (session["user_id"], meeting_id))
        if not cursor.rowcount:
            raise APIError("Favorite not found.", 404)
    return "", 204


@favorites_bp.get("")
@login_required
def list_favorites():
    with transaction() as cursor:
        cursor.execute("""SELECT m.meeting_id, m.title, m.meeting_date, m.meeting_time, m.location,
            m.status, s.sport_name FROM meeting_favorites f JOIN meetings m ON m.meeting_id = f.meeting_id
            JOIN sports s ON s.sport_id = m.sport_id WHERE f.user_id = %s
            ORDER BY f.created_at DESC, f.meeting_id DESC LIMIT %s OFFSET %s""", (session["user_id"], *pagination()))
        return {"favorites": [serialize(row) for row in cursor.fetchall()]}
