from flask import Blueprint, session

from app.shared.decorators import login_required
from .helpers import APIError, body, integer, lock_users, require_unblocked, transaction, user_pair

direct_chat_bp = Blueprint("direct_chat", __name__, url_prefix="/api/chat")


@direct_chat_bp.post("/direct")
@login_required
def create_direct_room():
    pair = user_pair(session["user_id"], integer(body().get("user_id"), "user_id"))
    with transaction() as cursor:
        lock_users(cursor, *pair)
        require_unblocked(cursor, *pair)
        cursor.execute("SELECT chat_room_id FROM chat_rooms WHERE direct_low = %s AND direct_high = %s", pair)
        room = cursor.fetchone()
        if room:
            return room, 200
        cursor.execute("INSERT INTO chat_rooms (room_type, direct_low, direct_high) VALUES ('DIRECT', %s, %s)", pair)
        room_id = cursor.lastrowid
        for user_id in pair:
            cursor.execute("INSERT INTO chat_room_members (chat_room_id, user_id) VALUES (%s, %s)", (room_id, user_id))
    return {"chat_room_id": room_id}, 201


def check_direct_send(cursor, chat_room_id, user_id):
    """Called inside the existing message transaction, AFTER membership check."""
    from .admin import check_active_user
    cursor.execute("SELECT room_type, direct_low, direct_high FROM chat_rooms WHERE chat_room_id = %s", (chat_room_id,))
    room = cursor.fetchone()
    if not room:
        raise APIError("Chat room not found.", 404)
    if room["room_type"] == "DIRECT":
        pair = (room["direct_low"], room["direct_high"])
        if user_id not in pair:
            raise APIError("Not a direct chat participant.", 403)
        lock_users(cursor, *pair)
        require_unblocked(cursor, *pair)
    else:
        lock_users(cursor, user_id)
    check_active_user(cursor, user_id)
