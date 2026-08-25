import unittest
from datetime import datetime
from unittest.mock import patch

from flask import Flask
from flask_socketio import SocketIO

from app.chat_dahyun.chat import chat_bp
from app.chat_dahyun.socket_events import _serialize_message, register_socket_events


class FakeCursor:
    def __init__(self, one_values=None, many=None):
        self.one_values = list(one_values or [])
        self.many = many or []
        self.executed = []
        self.lastrowid = 7

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        if not self.one_values:
            return None
        return self.one_values.pop(0)

    def fetchall(self):
        return self.many

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class ChatApiTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        app.register_blueprint(chat_bp)
        self.client = app.test_client()

        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def test_messages_query_uses_common_schema_names(self):
        cursor = FakeCursor(
            one_values=[{"member": 1}],
            many=[{
                "message_id": 7,
                "chat_room_id": 3,
                "sender_id": 1,
                "content": "hello",
                "created_at": "2026-08-26 12:00:00",
            }],
        )
        connection = FakeConnection(cursor)

        with patch(
            "app.chat_dahyun.chat.get_db_connection",
            return_value=connection,
        ):
            response = self.client.get("/api/chat/rooms/3/messages")

        self.assertEqual(response.status_code, 200)
        messages_sql = cursor.executed[1][0]
        self.assertIn("FROM chat_messages AS msg", messages_sql)
        self.assertIn("msg.created_at", messages_sql)
        self.assertNotIn("sent_at", messages_sql)


class ChatSocketTest(unittest.TestCase):
    def test_message_datetime_is_socket_json_serializable(self):
        message = _serialize_message({
            "message_id": 7,
            "created_at": datetime(2026, 8, 26, 12, 34, 56),
        })

        self.assertEqual(message["created_at"], "2026-08-26T12:34:56")

    def test_send_message_uses_common_schema_names(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        socketio = SocketIO(app, async_mode="threading")
        register_socket_events(socketio)
        flask_client = app.test_client()

        with flask_client.session_transaction() as session:
            session["user_id"] = 1

        cursor = FakeCursor(one_values=[
            {"member": 1},
            {
                "message_id": 7,
                "chat_room_id": 3,
                "sender_id": 1,
                "content": "hello",
                "created_at": "2026-08-26 12:00:00",
            },
        ])
        connection = FakeConnection(cursor)

        with patch(
            "app.chat_dahyun.socket_events.get_db_connection",
            return_value=connection,
        ):
            client = socketio.test_client(app, flask_test_client=flask_client)
            self.assertTrue(client.is_connected())
            client.emit("send_message", {
                "chat_room_id": 3,
                "content": "hello",
            })

        insert_sql = cursor.executed[1][0]
        select_sql = cursor.executed[2][0]
        self.assertIn("INSERT INTO chat_messages", insert_sql)
        self.assertIn("created_at", insert_sql)
        self.assertIn("FROM chat_messages AS msg", select_sql)
        self.assertIn("msg.created_at", select_sql)
        self.assertNotIn("sent_at", insert_sql + select_sql)
        self.assertTrue(connection.committed)


if __name__ == "__main__":
    unittest.main()
