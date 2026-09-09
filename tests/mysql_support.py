"""Opt-in integration tests against an isolated, disposable local MySQL instance.

TEST_MYSQL=1, TEST_MYSQL_PORT=3307. Never reads the application's .env DB settings.
The database name is fixed and all application connection factories are patched.
"""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import mysql.connector
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
DB_NAME = "yanawa_codex_test"
_initialized = False


def connect(database=DB_NAME):
    return mysql.connector.connect(host="127.0.0.1", port=int(os.getenv("TEST_MYSQL_PORT", "3307")),
                                   user="root", password=os.getenv("TEST_MYSQL_PASSWORD", ""),
                                   database=database, charset="utf8mb4", time_zone="+09:00")


def execute_script(connection, sql):
    cursor = connection.cursor()
    cursor.execute(sql)
    while cursor.nextset():
        if cursor.with_rows:
            cursor.fetchall()
    cursor.close()
    connection.commit()


@unittest.skipUnless(os.getenv("TEST_MYSQL") == "1", "Set TEST_MYSQL=1 for isolated MySQL integration tests")
class MySQLTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _initialized
        if not _initialized:
            connection = connect(None)
            cursor = connection.cursor()
            cursor.execute("DROP DATABASE IF EXISTS yanawa_codex_test")
            cursor.execute("CREATE DATABASE yanawa_codex_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cursor.execute("USE yanawa_codex_test")
            cursor.close()
            execute_script(connection, (ROOT / "database/init.sql").read_text(encoding="utf-8"))
            connection.close()
            _initialized = True
        from server import app, socketio
        cls.app, cls.socketio = app, socketio
        cls.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    def setUp(self):
        connection = connect()
        cursor = connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("SHOW TABLES")
        for (table,) in cursor.fetchall():
            cursor.execute(f"TRUNCATE TABLE `{table}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        for user_id in range(1, 7):
            cursor.execute("""INSERT INTO users (user_id, login_id, password, nickname, email,
                birth_date, gender, region, role) VALUES (%s,%s,%s,%s,%s,'2000-01-01','MALE','Seoul',%s)""",
                (user_id, f"user{user_id}", generate_password_hash("password123", method="pbkdf2:sha256:1000"),
                 f"tester{user_id}", f"user{user_id}@test.invalid", "ADMIN" if user_id == 6 else "USER"))
        cursor.execute("INSERT INTO sports (sport_id, sport_name) VALUES (1, 'Tennis')")
        cursor.execute("SHOW TABLES LIKE 'feature_locks'")
        if cursor.fetchone():
            cursor.execute("INSERT INTO feature_locks (lock_name) VALUES ('schedule'), ('sports')")
        connection.commit()
        cursor.close()
        connection.close()
        # Legacy modules imported their factory directly. No production configuration override.
        import sys
        for name, module in list(sys.modules.items()):
            if name.startswith("app.") and hasattr(module, "get_db_connection"):
                patcher = patch.object(module, "get_db_connection", connect)
                patcher.start()
                self.addCleanup(patcher.stop)
        self.client = self.client_for(1)

    def client_for(self, user_id):
        client = self.app.test_client()
        with client.session_transaction() as session:
            if user_id:
                session["user_id"] = user_id
        return client

    def sql(self, statement, params=()):
        connection = connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(statement, params)
        rows = cursor.fetchall() if cursor.with_rows else []
        connection.commit()
        cursor.close()
        connection.close()
        return rows

    def meeting(self, host=1, maximum=3, approval="INSTANT", start="10:00", end="11:00"):
        response = self.client_for(host).post("/api/meetings", json={
            "title": "Test meeting", "description": "Exercise", "sport_id": 1,
            "meeting_date": "2027-01-02", "meeting_time": start, "end_time": end,
            "location": "Seoul", "max_participants": maximum, "approval_type": approval})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["meeting_id"]
