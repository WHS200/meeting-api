import unittest

from flask import Flask

from app.auth_gyumin.auth import auth_bp
from app.shared.rate_limiter import limiter


class AuthRateLimitTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        limiter.init_app(app)
        app.register_blueprint(auth_bp)
        limiter.reset()

        self.client = app.test_client()
        self.addCleanup(limiter.reset)

    def test_login_same_ip_and_login_id_is_limited_after_five_requests(self):
        for _ in range(5):
            response = self.client.post(
                "/api/auth/login",
                json={"login_id": " SameUser "},
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            "/api/auth/login",
            json={"login_id": "sameuser"},
        )

        self.assertEqual(response.status_code, 429)

    def test_login_same_ip_is_limited_after_ten_different_login_ids(self):
        for index in range(10):
            response = self.client.post(
                "/api/auth/login",
                json={"login_id": f"user-{index}"},
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            "/api/auth/login",
            json={"login_id": "user-10"},
        )

        self.assertEqual(response.status_code, 429)

    def test_signup_same_ip_is_limited_after_five_requests(self):
        for _ in range(5):
            response = self.client.post("/api/auth/signup", json={})
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post("/api/auth/signup", json={})

        self.assertEqual(response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
