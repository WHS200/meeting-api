from flask import Blueprint, session

from app.shared.database import get_db_connection
from app.shared.decorators import login_required


chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _is_chat_room_member(cursor, chat_room_id, user_id):
    cursor.execute(
        """
        SELECT 1
        FROM chat_room_members
        WHERE chat_room_id = %s
        AND user_id = %s
        """,
        (chat_room_id, user_id)
    )

    return cursor.fetchone() is not None


@chat_bp.get("/rooms")
@login_required
def get_chat_rooms():
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                cr.chat_room_id,
                cr.room_type,
                cr.meeting_id,
                cr.created_at,
                m.title AS meeting_title
            FROM chat_room_members AS crm
            JOIN chat_rooms AS cr
                ON crm.chat_room_id = cr.chat_room_id
            LEFT JOIN meetings AS m
                ON cr.meeting_id = m.meeting_id
            WHERE crm.user_id = %s
            ORDER BY cr.created_at DESC
            """,
            (user_id,)
        )
        chat_rooms = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return {"chat_rooms": chat_rooms}, 200


@chat_bp.get("/rooms/<int:chat_room_id>/messages")
@login_required
def get_chat_messages(chat_room_id):
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if not _is_chat_room_member(cursor, chat_room_id, user_id):
            return {"message": "Chat room not found or access denied."}, 403

        cursor.execute(
            """
            SELECT
                msg.message_id,
                msg.chat_room_id,
                msg.sender_id,
                msg.content,
                msg.created_at,
                u.nickname AS sender_nickname,
                u.profile_image AS sender_profile_image
            FROM chat_messages AS msg
            JOIN users AS u
                ON msg.sender_id = u.user_id
            WHERE msg.chat_room_id = %s
            ORDER BY msg.created_at ASC, msg.message_id ASC
            """,
            (chat_room_id,)
        )
        messages = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return {"messages": messages}, 200


@chat_bp.get("/rooms/<int:chat_room_id>/members")
@login_required
def get_chat_room_members(chat_room_id):
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if not _is_chat_room_member(cursor, chat_room_id, user_id):
            return {"message": "Chat room not found or access denied."}, 403

        cursor.execute(
            """
            SELECT
                u.user_id,
                u.nickname,
                u.profile_image,
                crm.joined_at
            FROM chat_room_members AS crm
            JOIN users AS u
                ON crm.user_id = u.user_id
            WHERE crm.chat_room_id = %s
            ORDER BY crm.joined_at ASC, u.user_id ASC
            """,
            (chat_room_id,)
        )
        members = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return {"members": members}, 200
