import unittest
from datetime import timedelta
from unittest.mock import patch

from flask import Flask

from app.codex_features.helpers import APIError
from app.meetings_gyudong.meetings import _serialize_meeting, meetings_bp


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


class MeetingCreationCursor(FakeCursor):
    def __init__(self, fail_chat_member=False):
        super().__init__()
        self.fail_chat_member = fail_chat_member

    def execute(self, sql, params=()):
        super().execute(sql, params)

        if "INSERT INTO meetings" in sql:
            self.lastrowid = 41
        elif "INSERT INTO chat_rooms" in sql:
            self.lastrowid = 91
        elif "INSERT INTO chat_room_members" in sql and self.fail_chat_member:
            raise RuntimeError("chat member insert failed")

    def fetchone(self):
        return {"sport_id": 1}


class MeetingUpdateCursor(FakeCursor):
    def __init__(self, overlap=False):
        super().__init__(many=[])
        self.overlap = overlap
        self.current_sql = ""

    def execute(self, sql, params=()):
        super().execute(sql, params)
        self.current_sql = sql

    def fetchone(self):
        if "FROM meetings m" in self.current_sql:
            return {"meeting_id": 99} if self.overlap else None
        if "SELECT m.meeting_id, m.host_id" in self.current_sql:
            return {"meeting_id": 41, "host_id": 1, "role": "USER"}
        if "SELECT sport_id FROM sports" in self.current_sql:
            return {"sport_id": 1}
        if "SELECT host_id FROM meetings" in self.current_sql:
            return {"host_id": 1}
        return None


class MeetingsApiTest(unittest.TestCase):
    def setUp(self):
        patcher = patch("app.meetings_gyudong.meetings.lock_schedule")
        patcher.start()
        self.addCleanup(patcher.stop)
        overlap_patcher = patch("app.meetings_gyudong.meetings.ensure_no_overlap")
        overlap_patcher.start()
        self.addCleanup(overlap_patcher.stop)
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        app.register_error_handler(APIError, lambda error: ({"message": error.message}, error.status))
        app.register_blueprint(meetings_bp)
        self.client = app.test_client()

    def _valid_meeting_payload(self):
        return {
            "title": "한강 러닝",
            "description": "5km 러닝",
            "sport_id": 1,
            "meeting_date": "2099-08-30",
            "meeting_time": "19:30",
            "end_time": "20:30",
            "location": "여의도",
            "max_participants": 4,
            "required_skill_level": "SILVER",
            "approval_type": "APPROVAL",
        }

    def _login(self, user_id=1):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id

    def test_meeting_counts_include_host_and_clamp_remaining_slots(self):
        meeting = {"max_participants": 6, "approved_count": 2}
        self.assertEqual(_serialize_meeting(meeting)["participant_count"], 3)
        self.assertEqual(meeting["remaining_slots"], 3)
        overfull = {"max_participants": 2, "approved_count": 5}
        self.assertEqual(_serialize_meeting(overfull)["remaining_slots"], 0)

    def test_create_meeting_creates_chat_room_and_adds_host(self):
        self._login(user_id=7)
        cursor = MeetingCreationCursor()
        connection = FakeConnection(cursor)

        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ):
            response = self.client.post(
                "/api/meetings",
                json=self._valid_meeting_payload(),
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["meeting_id"], 41)
        self.assertTrue(connection.committed)
        sql_statements = [sql for sql, _ in cursor.executed]
        self.assertTrue(any("INSERT INTO meetings" in sql for sql in sql_statements))
        self.assertTrue(any("INSERT INTO chat_rooms" in sql for sql in sql_statements))
        self.assertTrue(any("INSERT INTO chat_room_members" in sql for sql in sql_statements))
        chat_room_params = next(
            params
            for sql, params in cursor.executed
            if "INSERT INTO chat_rooms" in sql
        )
        member_params = next(
            params
            for sql, params in cursor.executed
            if "INSERT INTO chat_room_members" in sql
        )
        self.assertEqual(chat_room_params, ("MEETING", 41))
        self.assertEqual(member_params, (91, 7))
        meeting_sql, meeting_params = next(
            (sql, params)
            for sql, params in cursor.executed
            if "INSERT INTO meetings" in sql
        )
        self.assertIn("required_skill_level", meeting_sql)
        self.assertIn("SILVER", meeting_params)

    def test_create_meeting_rolls_back_if_chat_member_insert_fails(self):
        self._login(user_id=7)
        cursor = MeetingCreationCursor(fail_chat_member=True)
        connection = FakeConnection(cursor)

        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/api/meetings",
                    json=self._valid_meeting_payload(),
                )

        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    def test_create_meeting_rejects_past_start_time(self):
        self._login()
        payload = self._valid_meeting_payload()
        payload.update(meeting_date="2000-01-01", meeting_time="10:00", end_time="11:00")
        response = self.client.post("/api/meetings", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_delete_meeting_relies_on_foreign_key_cascades(self):
        self._login(user_id=7)
        cursor = FakeCursor(one={
            "meeting_id": 41,
            "host_id": 7,
            "role": "USER",
        })
        connection = FakeConnection(cursor)

        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ):
            response = self.client.delete("/api/meetings/41")

        self.assertEqual(response.status_code, 204)
        delete_sql = [sql for sql, _ in cursor.executed if "DELETE FROM" in sql]
        self.assertEqual(len(delete_sql), 1)
        self.assertIn("DELETE FROM meetings", delete_sql[0])
        self.assertNotIn("meeting_participants", delete_sql[0])
        self.assertTrue(connection.committed)

    def test_update_meeting_does_not_require_status(self):
        self._login()
        cursor = MeetingUpdateCursor()
        connection = FakeConnection(cursor)

        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ), patch("app.meetings_gyudong.meetings.notify_meeting_changes"), patch(
            "app.meetings_gyudong.meetings.promote_waiters"
        ):
            response = self.client.put(
                "/api/meetings/41",
                json=self._valid_meeting_payload(),
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(connection.committed)

    def test_update_meeting_canceled_body_does_not_skip_overlap_check(self):
        self._login()
        cursor = MeetingUpdateCursor(overlap=True)
        connection = FakeConnection(cursor)
        payload = self._valid_meeting_payload()
        payload["status"] = "CANCELED"

        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ), patch("app.meetings_gyudong.meetings.notify_meeting_changes"), patch(
            "app.meetings_gyudong.meetings.promote_waiters"
        ):
            response = self.client.put("/api/meetings/41", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertTrue(connection.rolled_back)
        self.assertFalse(any("SET sport_id" in sql for sql, _ in cursor.executed))

    def test_list_meetings(self):
        cursor = FakeCursor(many=[{
            "meeting_id": 1,
            "title": "한강 러닝",
            "meeting_time": timedelta(hours=19, minutes=30),
        }])
        connection = FakeConnection(cursor)
        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ):
            response = self.client.get("/api/meetings?keyword=한강&status=recruiting")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)
        self.assertEqual(
            response.get_json()["meetings"][0]["meeting_time"],
            "19:30",
        )
        sql, params = next(
            (sql, params) for sql, params in cursor.executed if "m.title LIKE %s" in sql
        )
        self.assertIn("m.title LIKE %s", sql)
        self.assertEqual(params, ("%한강%", "%한강%", "RECRUITING"))

    def test_invalid_date_filter(self):
        response = self.client.get("/api/meetings?date=2026-99-99")
        self.assertEqual(response.status_code, 400)

    def test_create_requires_login(self):
        response = self.client.post("/api/meetings", json={})
        self.assertEqual(response.status_code, 401)

    def test_create_validates_meeting_time(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1

        response = self.client.post(
            "/api/meetings",
            json={
                "title": "한강 러닝",
                "description": "5km 러닝",
                "sport_id": 1,
                "meeting_date": "2026-08-30",
                "meeting_time": "25:30",
                "location": "여의도",
                "max_participants": 10,
                "required_skill_level": "SILVER",
                "approval_type": "APPROVAL",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["message"],
            "meeting_time should be HH:MM.",
        )

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
                "meeting_time": "19:30",
                "location": "여의도",
                "max_participants": 10,
                "required_skill_level": "SILVER",
                "approval_type": "APPROVAL",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_create_validates_required_skill_level(self):
        self._login()
        payload = self._valid_meeting_payload()
        payload["required_skill_level"] = "EXPERT"

        response = self.client.post("/api/meetings", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("required_skill_level", response.get_json()["message"])

    def test_create_allows_null_required_skill_level(self):
        self._login()
        payload = self._valid_meeting_payload()
        payload["required_skill_level"] = None
        cursor = MeetingCreationCursor()
        connection = FakeConnection(cursor)

        with patch(
            "app.meetings_gyudong.meetings.get_db_connection",
            return_value=connection,
        ):
            response = self.client.post("/api/meetings", json=payload)

        self.assertEqual(response.status_code, 201)
        meeting_params = next(
            params
            for sql, params in cursor.executed
            if "INSERT INTO meetings" in sql
        )
        self.assertIsNone(meeting_params[-2])


if __name__ == "__main__":
    unittest.main()
