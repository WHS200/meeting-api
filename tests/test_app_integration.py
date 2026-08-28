import runpy
import unittest
from pathlib import Path


class AppIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entrypoint = Path(__file__).resolve().parents[1] / "server.py"
        namespace = runpy.run_path(str(entrypoint))
        cls.app = namespace["app"]
        cls.socketio = namespace["socketio"]
        cls.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    def test_all_blueprints_are_registered(self):
        rules = {rule.rule for rule in self.app.url_map.iter_rules()}

        self.assertIn("/api/auth/login", rules)
        self.assertIn("/api/users/me", rules)
        self.assertIn("/api/meetings", rules)
        self.assertIn("/api/meetings/<int:meeting_id>/participants", rules)
        self.assertIn("/api/chat/rooms", rules)

    def test_existing_protected_apis_still_require_login(self):
        client = self.app.test_client()

        self.assertEqual(client.get("/api/users/me").status_code, 401)
        self.assertEqual(client.post("/api/meetings", json={}).status_code, 401)
        self.assertEqual(
            client.post("/api/meetings/1/participants").status_code,
            401,
        )
        self.assertEqual(client.get("/api/chat/rooms").status_code, 401)

    def test_socket_events_are_registered(self):
        handlers = self.socketio.server.handlers["/"]

        self.assertIn("connect", handlers)
        self.assertIn("join_room", handlers)
        self.assertIn("leave_room", handlers)
        self.assertIn("send_message", handlers)
        self.assertIn("disconnect", handlers)


if __name__ == "__main__":
    unittest.main()
