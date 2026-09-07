from flask import Blueprint, request, session

from app.shared.decorators import login_required
from .helpers import (APIError, body, integer, lock_users, pagination,
                      public_users, require_unblocked, transaction, user_pair)

friends_bp = Blueprint("friends", __name__, url_prefix="/api/friends")
from .notifications import notify


@friends_bp.get("/search")
@login_required
def search_users():
    keyword = request.args.get("nickname", "").strip()
    if not 1 <= len(keyword) <= 50:
        raise APIError("nickname must contain 1 to 50 characters.")
    with transaction() as cursor:
        cursor.execute("""SELECT user_id, nickname, profile_image FROM users
            WHERE status = 'ACTIVE' AND user_id != %s AND nickname LIKE %s
            ORDER BY nickname LIMIT %s OFFSET %s""",
            (session["user_id"], f"%{keyword}%", *pagination()))
        return {"users": public_users(cursor.fetchall())}


@friends_bp.post("/requests")
@login_required
def send_request():
    sender = session["user_id"]
    recipient = integer(body().get("user_id"), "user_id")
    pair = user_pair(sender, recipient)
    with transaction() as cursor:
        lock_users(cursor, *pair)
        require_unblocked(cursor, *pair)
        cursor.execute("SELECT 1 FROM friendships WHERE user_low = %s AND user_high = %s", pair)
        if cursor.fetchone():
            raise APIError("Already friends.", 409)
        cursor.execute("""SELECT 1 FROM friend_requests
            WHERE pending_low = %s AND pending_high = %s""", pair)
        if cursor.fetchone():
            raise APIError("A pending request already exists in either direction.", 409)
        cursor.execute("INSERT INTO friend_requests (sender_id, recipient_id) VALUES (%s, %s)", (sender, recipient))
        request_id = cursor.lastrowid
        notify(cursor, recipient, "FRIEND_REQUEST", "새로운 친구 요청이 도착했습니다.", "FRIEND_REQUEST", request_id)
    return {"request_id": request_id}, 201


@friends_bp.get("/requests")
@login_required
def list_requests():
    direction = request.args.get("direction", "received")
    if direction not in ("received", "sent"):
        raise APIError("direction must be received or sent.")
    # Column names come exclusively from this allowlist.
    owner, other = ("recipient_id", "sender_id") if direction == "received" else ("sender_id", "recipient_id")
    with transaction() as cursor:
        cursor.execute(f"""SELECT r.request_id, r.sender_id, r.recipient_id, r.created_at,
            u.user_id, u.nickname, u.profile_image FROM friend_requests r
            JOIN users u ON u.user_id = r.{other}
            WHERE r.{owner} = %s AND r.status = 'PENDING'
            ORDER BY r.request_id DESC LIMIT %s OFFSET %s""", (session["user_id"], *pagination()))
        return {"requests": public_users(cursor.fetchall())}


@friends_bp.post("/requests/<int:request_id>/<action>")
@login_required
def handle_request(request_id, action):
    if action not in ("accept", "reject", "cancel"):
        raise APIError("Unknown action.", 404)
    with transaction() as cursor:
        cursor.execute("SELECT * FROM friend_requests WHERE request_id = %s", (request_id,))
        row = cursor.fetchone()
        if not row:
            raise APIError("Request not found.", 404)
        owner = row["sender_id"] if action == "cancel" else row["recipient_id"]
        if owner != session["user_id"]:
            raise APIError("Not authorized.", 403)
        pair = user_pair(row["sender_id"], row["recipient_id"])
        lock_users(cursor, *pair)
        # Current locking read after pair lock, including concurrent block/cancel.
        cursor.execute("SELECT status FROM friend_requests WHERE request_id = %s FOR UPDATE", (request_id,))
        if cursor.fetchone()["status"] != "PENDING":
            raise APIError("Request already processed.", 409)
        if action == "accept":
            require_unblocked(cursor, *pair)
            cursor.execute("INSERT INTO friendships (user_low, user_high) VALUES (%s, %s)", pair)
        status = {"accept": "ACCEPTED", "reject": "REJECTED", "cancel": "CANCELED"}[action]
        cursor.execute("UPDATE friend_requests SET status = %s WHERE request_id = %s", (status, request_id))
        if action == "accept":
            notify(cursor, row["sender_id"], "FRIEND_ACCEPTED", "친구 요청이 수락되었습니다.", "USER", row["recipient_id"])
    return {"status": status}


@friends_bp.get("")
@login_required
def list_friends():
    user_id = session["user_id"]
    with transaction() as cursor:
        cursor.execute("""SELECT u.user_id, u.nickname, u.profile_image FROM friendships f
            JOIN users u ON u.user_id = CASE WHEN f.user_low = %s THEN f.user_high ELSE f.user_low END
            WHERE (f.user_low = %s OR f.user_high = %s) AND u.status != 'DELETED'
            ORDER BY u.nickname LIMIT %s OFFSET %s""", (user_id, user_id, user_id, *pagination()))
        return {"friends": public_users(cursor.fetchall())}


@friends_bp.delete("/<int:user_id>")
@login_required
def delete_friend(user_id):
    pair = user_pair(session["user_id"], user_id)
    with transaction() as cursor:
        lock_users(cursor, *pair)
        cursor.execute("DELETE FROM friendships WHERE user_low = %s AND user_high = %s", pair)
        if not cursor.rowcount:
            raise APIError("Friend not found.", 404)
    return "", 204
