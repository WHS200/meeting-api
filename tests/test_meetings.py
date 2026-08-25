import unittest
from unittest.mock import patch

from flask import Flask

from app.meetings_gyudong.meetings import meetings_bp


class FakeCursor:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or []
        self.executed = []
        self.lastrowid = 3

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.one

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


class MeetingsApiTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        app.register_blueprint(meetings_bp)
        self.client = app.test_client()

    def test_list_meetings(self):
        cursor = FakeCursor(many=[{"meeting_id": 1, "title": "한강 러닝"}])
        connection = FakeConnection(cursor)
        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ):
            response = self.client.get("/api/meetings?keyword=한강&status=recruiting")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)
        sql, params = cursor.executed[0]
        self.assertIn("m.title LIKE %s", sql)
        self.assertEqual(params, ("%한강%", "%한강%", "RECRUITING"))

    def test_invalid_date_filter(self):
        response = self.client.get("/api/meetings?date=2026-99-99")
        self.assertEqual(response.status_code, 400)

    def test_create_requires_login(self):
        response = self.client.post("/api/meetings", json={})
        self.assertEqual(response.status_code, 401)

    def test_create_validates_integer_fields(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1

        response = self.client.post(
            "/api/meetings",
            json={
                "title": "한강 러닝",
                "description": "5km 러닝",
                "sport_id": "1",
                "meeting_date": "2026-08-30",
                "location": "여의도",
                "max_participants": 10,
                "approval_type": "APPROVAL",
            },
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
