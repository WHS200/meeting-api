from flask import session
from flask_socketio import disconnect as disconnect_client
from flask_socketio import emit, join_room, leave_room

from app.shared.database import get_db_connection


def _get_chat_room_id(data):
    if not isinstance(data, dict):
        return None

    chat_room_id = data.get("chat_room_id")

    if isinstance(chat_room_id, bool) or not isinstance(chat_room_id, int):
        return None

    return chat_room_id


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


def _check_membership(chat_room_id, user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        return _is_chat_room_member(
            cursor,
            chat_room_id,
            user_id
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def register_socket_events(socketio):
    @socketio.on("connect")
    def handle_connect():
        user_id = session.get("user_id")

        if user_id is None:
            return False

        emit("connected", {"user_id": user_id})
        return None

    @socketio.on("join_room")
    def handle_join_room(data):
        user_id = session.get("user_id")

        if user_id is None:
            emit("error", {"message": "Login first."})
            disconnect_client()
            return

        chat_room_id = _get_chat_room_id(data)

        if chat_room_id is None:
            emit("error", {"message": "Valid chat_room_id is required."})
            return

        try:
            is_member = _check_membership(chat_room_id, user_id)
        except Exception:
            emit("error", {"message": "Failed to check chat room membership."})
            return

        if not is_member:
            emit("error", {"message": "Chat room not found or access denied."})
            return

        join_room(str(chat_room_id))
        emit("joined_room", {"chat_room_id": chat_room_id})

    @socketio.on("leave_room")
    def handle_leave_room(data):
        user_id = session.get("user_id")

        if user_id is None:
            emit("error", {"message": "Login first."})
            disconnect_client()
            return

        chat_room_id = _get_chat_room_id(data)

        if chat_room_id is None:
            emit("error", {"message": "Valid chat_room_id is required."})
            return

        try:
            is_member = _check_membership(chat_room_id, user_id)
        except Exception:
            emit("error", {"message": "Failed to check chat room membership."})
            return

        if not is_member:
            emit("error", {"message": "Chat room not found or access denied."})
            return

        leave_room(str(chat_room_id))
        emit("left_room", {"chat_room_id": chat_room_id})

    @socketio.on("send_message")
    def handle_send_message(data):
        user_id = session.get("user_id")

        if user_id is None:
            emit("error", {"message": "Login first."})
            disconnect_client()
            return

        chat_room_id = _get_chat_room_id(data)

        if chat_room_id is None:
            emit("error", {"message": "Valid chat_room_id is required."})
            return

        content = data.get("content")

        if not isinstance(content, str) or not content.strip():
            emit("error", {"message": "Message content is required."})
            return

        content = content.strip()

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            if not _is_chat_room_member(cursor, chat_room_id, user_id):
                emit(
                    "error",
                    {"message": "Chat room not found or access denied."}
                )
                return

            cursor.execute(
                """
                INSERT INTO messages (
                    chat_room_id,
                    sender_id,
                    content,
                    sent_at
                )
                VALUES (%s, %s, %s, NOW())
                """,
                (chat_room_id, user_id, content)
            )
            message_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT
                    msg.message_id,
                    msg.chat_room_id,
                    msg.sender_id,
                    msg.content,
                    msg.sent_at,
                    u.nickname AS sender_nickname,
                    u.profile_image AS sender_profile_image
                FROM messages AS msg
                JOIN users AS u
                    ON msg.sender_id = u.user_id
                WHERE msg.message_id = %s
                """,
                (message_id,)
            )
            message = cursor.fetchone()

            connection.commit()
        except Exception:
            connection.rollback()
            emit("error", {"message": "Failed to save message."})
            return
        finally:
            cursor.close()
            connection.close()

        socketio.emit(
            "receive_message",
            message,
            to=str(chat_room_id)
        )

    @socketio.on("disconnect")
    def handle_disconnect():
        return None
