from mysql_support import MySQLTestCase


class SessionVersionTest(MySQLTestCase):
    def login(self):
        client = self.app.test_client()

        response = client.post(
            "/api/auth/login",
            json={
                "login_id": "user1",
                "password": "password123"
            }
        )

        self.assertEqual(
            response.status_code,
            200,
            response.get_json()
        )

        return client

    def test_logout_invalidates_old_session(self):
        client = self.login()

        # 로그아웃 전에 발급된 세션 내용을 저장
        with client.session_transaction() as session:
            old_user_id = session["user_id"]
            old_session_version = session["session_version"]

        before = self.sql(
            """
            SELECT session_version
            FROM users
            WHERE user_id = 1
            """
        )[0]["session_version"]

        response = client.post(
            "/api/auth/logout"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        after = self.sql(
            """
            SELECT session_version
            FROM users
            WHERE user_id = 1
            """
        )[0]["session_version"]

        self.assertEqual(
            after,
            before + 1
        )

        # 공격자가 복사해 둔 예전 세션을 다시 넣는 상황 재현
        with client.session_transaction() as session:
            session["user_id"] = old_user_id
            session["session_version"] = old_session_version

        response = client.get(
            "/api/users/me"
        )

        self.assertEqual(
            response.status_code,
            401
        )

    def test_password_change_invalidates_other_session(self):
        browser_a = self.login()
        browser_b = self.login()

        response = browser_b.patch(
            "/api/users/me/password",
            json={
                "current_password": "password123",
                "new_password": "newpassword123"
            }
        )

        self.assertEqual(
            response.status_code,
            200,
            response.get_json()
        )

        # 비밀번호 변경 전에 로그인한 다른 브라우저
        response_a = browser_a.get(
            "/api/users/me"
        )

        self.assertEqual(
            response_a.status_code,
            401
        )

        # 비밀번호를 직접 변경한 현재 브라우저
        response_b = browser_b.get(
            "/api/users/me"
        )

        self.assertEqual(
            response_b.status_code,
            200
        )

    def test_session_without_version_is_rejected(self):
        client = self.app.test_client()

        # 기존 배포에서 발급된 옛날 세션을 가정
        with client.session_transaction() as session:
            session["user_id"] = 1

        response = client.get(
            "/api/users/me"
        )

        self.assertEqual(
            response.status_code,
            401
        )


if __name__ == "__main__":
    import unittest
    unittest.main()