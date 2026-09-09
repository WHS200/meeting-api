from flask import Blueprint, request, session

from app.shared.database import get_db_connection
from app.shared.decorators import login_required
from app.shared.s3 import generate_profile_image_url # S3


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
                m.title AS meeting_title,
                m.status AS meeting_status,
                m.host_id AS meeting_host_id,
                direct_user.nickname AS direct_nickname,
                direct_user.profile_image AS direct_profile_image
            FROM chat_room_members AS crm
            JOIN chat_rooms AS cr
                ON crm.chat_room_id = cr.chat_room_id
            LEFT JOIN meetings AS m
                ON cr.meeting_id = m.meeting_id
            LEFT JOIN chat_room_members AS direct_member
                ON direct_member.chat_room_id = cr.chat_room_id
                AND cr.room_type = 'DIRECT'
                AND direct_member.user_id != %s
            LEFT JOIN users AS direct_user
                ON direct_user.user_id = direct_member.user_id
            WHERE crm.user_id = %s
            ORDER BY cr.created_at DESC
            """,
            (user_id, user_id)
        )
        chat_rooms = cursor.fetchall()
        for room in chat_rooms:
            room["direct_profile_image"] = (
                generate_profile_image_url(room.get("direct_profile_image"))
            )
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

        try:
            limit = int(request.args.get("limit", 50))
            if limit < 1 or limit > 100:
                raise ValueError
        except (TypeError, ValueError):
            return {"message": "limit must be between 1 and 100."}, 400
        before = request.args.get("before_message_id", type=int)
        params = [chat_room_id]
        before_clause = ""
        if before is not None:
            if before < 1:
                return {"message": "before_message_id must be positive."}, 400
            before_clause = " AND msg.message_id < %s"
            params.append(before)
        params.append(limit + 1)
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
            """ + before_clause + """
            ORDER BY msg.message_id DESC
            LIMIT %s
            """,
            tuple(params)
        )
        messages = cursor.fetchall()
        has_more = len(messages) > limit
        messages = list(reversed(messages[:limit]))

        # S3 이미지 확인
        for message in messages:
            message["sender_profile_image"] = (
                generate_profile_image_url(message.get("sender_profile_image"))
            )

    finally:
        cursor.close()
        connection.close()

    return {"messages": messages, "has_more": has_more, "next_before_message_id": messages[0]["message_id"] if has_more and messages else None}, 200


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

        # S3 이미지
        for member in members:
            member["profile_image"] = (
                generate_profile_image_url(member.get("profile_image"))
            )

    finally:
        cursor.close()
        connection.close()

    return {"members": members}, 200
