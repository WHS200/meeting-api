import unittest
from unittest.mock import patch

from flask import Flask

from app.participation_euna.participation import participation_bp


class FakeCursor:
    def __init__(self, one_values=None, fail_on=None):
        self.one_values = list(one_values or [])
        self.fail_on = fail_on
        self.executed = []
        self.closed = False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("forced database failure")

    def fetchone(self):
        if not self.one_values:
            return None
        return self.one_values.pop(0)

    def fetchall(self):
        return []

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class ParticipationChatIntegrationTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        app.register_blueprint(participation_bp)
        self.client = app.test_client()

    def _meeting(self, approval_type="APPROVAL", status="RECRUITING", maximum=4):
        return {
            "meeting_id": 10,
            "host_id": 1,
            "approval_type": approval_type,
            "status": status,
            "max_participants": maximum,
        }

    def _request(self, method, path, user_id, one_values, fail_on=None):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

        cursor = FakeCursor(one_values=one_values, fail_on=fail_on)
        connection = FakeConnection(cursor)
        self.last_connection = connection
        with patch(
            "app.participation_euna.helpers.get_db_connection",
            return_value=connection,
        ):
            response = self.client.open(path, method=method)

        return response, connection, cursor

    def _sql(self, cursor):
        return "\n".join(sql for sql, _ in cursor.executed)

    def test_instant_join_approves_and_adds_chat_member(self):
        response, connection, cursor = self._request(
            "POST",
            "/api/meetings/10/participants",
            user_id=2,
            one_values=[
                self._meeting(approval_type="INSTANT"),
                None,
                {"count": 0},
                {"chat_room_id": 20},
            ],
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["participation_status"], "APPROVED")
        self.assertIn("INSERT INTO meeting_participants", self._sql(cursor))
        self.assertIn("INSERT IGNORE INTO chat_room_members", self._sql(cursor))
        self.assertIn("FOR UPDATE", cursor.executed[0][0])
        self.assertTrue(connection.committed)

    def test_approval_join_stays_pending_without_chat_member(self):
        response, connection, cursor = self._request(
            "POST",
            "/api/meetings/10/participants",
            user_id=2,
            one_values=[
                self._meeting(approval_type="APPROVAL"),
                None,
                {"count": 0},
            ],
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["participation_status"], "PENDING")
        self.assertNotIn("chat_room_members", self._sql(cursor))
        self.assertTrue(connection.committed)

    def test_approve_updates_status_and_adds_chat_member(self):
        response, connection, cursor = self._request(
            "POST",
            "/api/meetings/10/participants/2/approve",
            user_id=1,
            one_values=[
                self._meeting(),
                {"count": 0},
                {"participation_status": "PENDING"},
                {"chat_room_id": 20},
            ],
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("SET participation_status = %s", self._sql(cursor))
        self.assertIn("INSERT IGNORE INTO chat_room_members", self._sql(cursor))
        self.assertIn("FOR UPDATE", cursor.executed[0][0])
        self.assertTrue(connection.committed)

    def test_cancel_updates_status_and_removes_chat_member(self):
        response, connection, cursor = self._request(
            "DELETE",
            "/api/meetings/10/participants/me",
            user_id=2,
            one_values=[
                self._meeting(),
                {"participation_status": "APPROVED"},
            ],
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("participation_status = 'CANCELED'", self._sql(cursor))
        self.assertIn("DELETE FROM chat_room_members", self._sql(cursor))
        self.assertTrue(connection.committed)

    def test_kick_updates_status_and_removes_chat_member(self):
        response, connection, cursor = self._request(
            "DELETE",
            "/api/meetings/10/participants/2",
            user_id=1,
            one_values=[
                self._meeting(),
                {"participation_status": "APPROVED"},
            ],
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("participation_status = 'KICKED'", self._sql(cursor))
        self.assertIn("DELETE FROM chat_room_members", self._sql(cursor))
        self.assertTrue(connection.committed)

    def test_non_recruiting_meetings_reject_join(self):
        for status in ("CLOSED", "COMPLETED", "CANCELED"):
            with self.subTest(status=status):
                response, connection, cursor = self._request(
                    "POST",
                    "/api/meetings/10/participants",
                    user_id=2,
                    one_values=[self._meeting(status=status)],
                )

                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["message"],
                    "Meeting is not recruiting.",
                )
                self.assertFalse(connection.committed)
                self.assertNotIn("INSERT INTO meeting_participants", self._sql(cursor))

    def test_non_recruiting_meetings_reject_approval(self):
        for status in ("CLOSED", "COMPLETED", "CANCELED"):
            with self.subTest(status=status):
                response, connection, cursor = self._request(
                    "POST",
                    "/api/meetings/10/participants/2/approve",
                    user_id=1,
                    one_values=[self._meeting(status=status)],
                )

                self.assertEqual(response.status_code, 409)
                self.assertEqual(
                    response.get_json()["message"],
                    "Meeting is not recruiting.",
                )
                self.assertFalse(connection.committed)
                self.assertNotIn("UPDATE meeting_participants", self._sql(cursor))

    def test_capacity_includes_host_for_join_and_approval(self):
        allowed_join, _, _ = self._request(
            "POST",
            "/api/meetings/10/participants",
            user_id=4,
            one_values=[
                self._meeting(approval_type="INSTANT", maximum=4),
                None,
                {"count": 2},
                {"chat_room_id": 20},
            ],
        )
        full_join, _, _ = self._request(
            "POST",
            "/api/meetings/10/participants",
            user_id=5,
            one_values=[
                self._meeting(approval_type="INSTANT", maximum=4),
                None,
                {"count": 3},
            ],
        )
        allowed_approval, _, _ = self._request(
            "POST",
            "/api/meetings/10/participants/4/approve",
            user_id=1,
            one_values=[
                self._meeting(maximum=4),
                {"count": 2},
                {"participation_status": "PENDING"},
                {"chat_room_id": 20},
            ],
        )
        full_approval, _, _ = self._request(
            "POST",
            "/api/meetings/10/participants/5/approve",
            user_id=1,
            one_values=[
                self._meeting(maximum=4),
                {"count": 3},
            ],
        )

        self.assertEqual(allowed_join.status_code, 201)
        self.assertEqual(full_join.status_code, 409)
        self.assertEqual(allowed_approval.status_code, 200)
        self.assertEqual(full_approval.status_code, 409)

    def test_host_cannot_join_own_meeting(self):
        response, connection, cursor = self._request(
            "POST",
            "/api/meetings/10/participants",
            user_id=1,
            one_values=[self._meeting()],
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["message"],
            "Host cannot participate in own meeting.",
        )
        self.assertFalse(connection.committed)
        self.assertNotIn("INSERT INTO meeting_participants", self._sql(cursor))

    def test_chat_membership_failure_rolls_back_participation(self):
        with self.assertRaises(RuntimeError):
            self._request(
                "POST",
                "/api/meetings/10/participants",
                user_id=2,
                one_values=[
                    self._meeting(approval_type="INSTANT"),
                    None,
                    {"count": 0},
                    {"chat_room_id": 20},
                ],
                fail_on="INSERT IGNORE INTO chat_room_members",
            )

        self.assertTrue(self.last_connection.rolled_back)
        self.assertFalse(self.last_connection.committed)

    def test_chat_member_removal_failure_rolls_back_cancellation(self):
        with self.assertRaises(RuntimeError):
            self._request(
                "DELETE",
                "/api/meetings/10/participants/me",
                user_id=2,
                one_values=[
                    self._meeting(),
                    {"participation_status": "APPROVED"},
                ],
                fail_on="DELETE FROM chat_room_members",
            )

        self.assertTrue(self.last_connection.rolled_back)
        self.assertFalse(self.last_connection.committed)


if __name__ == "__main__":
    unittest.main()
