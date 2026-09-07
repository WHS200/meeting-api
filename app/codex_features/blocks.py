from flask import Blueprint, session

from app.shared.decorators import login_required
from .helpers import APIError, lock_users, pagination, public_users, transaction, user_pair

blocks_bp = Blueprint("blocks", __name__, url_prefix="/api/blocks")


@blocks_bp.post("/<int:user_id>")
@login_required
def block_user(user_id):
    actor = session["user_id"]
    pair = user_pair(actor, user_id)
    with transaction() as cursor:
        lock_users(cursor, *pair)
        cursor.execute("INSERT INTO user_blocks (blocker_id, blocked_id) VALUES (%s, %s)", (actor, user_id))
        cursor.execute("DELETE FROM friendships WHERE user_low = %s AND user_high = %s", pair)
        cursor.execute("""UPDATE friend_requests SET status = 'CANCELED'
            WHERE pending_low = %s AND pending_high = %s""", pair)
    return {"message": "User blocked."}, 201


@blocks_bp.delete("/<int:user_id>")
@login_required
def unblock_user(user_id):
    pair = user_pair(session["user_id"], user_id)
    with transaction() as cursor:
        lock_users(cursor, *pair)
        cursor.execute("DELETE FROM user_blocks WHERE blocker_id = %s AND blocked_id = %s", (session["user_id"], user_id))
        if not cursor.rowcount:
            raise APIError("Your block was not found.", 404)
    return "", 204


@blocks_bp.get("")
@login_required
def list_blocks():
    with transaction() as cursor:
        cursor.execute("""SELECT u.user_id, u.nickname, u.profile_image, b.created_at
            FROM user_blocks b JOIN users u ON u.user_id = b.blocked_id
            WHERE b.blocker_id = %s ORDER BY b.created_at DESC
            LIMIT %s OFFSET %s""", (session["user_id"], *pagination()))
        return {"blocks": public_users(cursor.fetchall())}
