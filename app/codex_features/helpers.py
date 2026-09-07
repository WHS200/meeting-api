"""Small shared validation and transaction helpers; all SQL uses bound values."""
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta

from flask import request
from mysql.connector import Error as MySQLError

from app.shared.database import get_db_connection
from app.shared.s3 import generate_profile_image_url


class APIError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


@contextmanager
def transaction():
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        yield cursor
        connection.commit()
    except MySQLError as error:
        connection.rollback()
        if error.errno in (1062, 1213, 1205):
            raise APIError("Conflicting request. Refresh and retry.", 409) from error
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("JSON object required.")
    return data


def text_field(data, key, minimum=1, maximum=1000):
    value = data.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise APIError(f"{key} must contain {minimum} to {maximum} characters.")
    return value.strip()


def integer(value, name="id", minimum=1, maximum=2147483647):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise APIError(f"Invalid {name}.")
    return value


def choice(value, allowed, name):
    if not isinstance(value, str) or value not in allowed:
        raise APIError(f"Invalid {name}.")
    return value


def pagination():
    try:
        limit = int(request.args.get("limit", "30"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        raise APIError("Invalid pagination.")
    if not 1 <= limit <= 100 or not 0 <= offset <= 1000000:
        raise APIError("Invalid pagination.")
    return limit, offset


def user_pair(user_id, target_id):
    integer(target_id, "user_id")
    if user_id == target_id:
        raise APIError("Cannot target yourself.", 409)
    return tuple(sorted((user_id, target_id)))


def lock_users(cursor, *user_ids):
    # Same ascending lock order for friend/block/direct operations.
    for user_id in sorted(set(user_ids)):
        cursor.execute("SELECT user_id, status FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
        user = cursor.fetchone()
        if user is None or user["status"] == "DELETED":
            raise APIError("User not found.", 404)


def blocked(cursor, first, second):
    cursor.execute("""SELECT 1 FROM user_blocks
        WHERE (blocker_id = %s AND blocked_id = %s)
           OR (blocker_id = %s AND blocked_id = %s) LIMIT 1 FOR UPDATE""",
        (first, second, second, first))
    return cursor.fetchone() is not None


def require_unblocked(cursor, first, second):
    if blocked(cursor, first, second):
        raise APIError("Blocked relationship.", 403)


def public_users(rows):
    for row in rows:
        row["profile_image"] = generate_profile_image_url(row.get("profile_image"))
    return rows


def serialize(row):
    if row is None:
        return None
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (datetime, date, time)):
            result[key] = value.isoformat()
        elif isinstance(value, timedelta):
            seconds = int(value.total_seconds())
            result[key] = f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"
    return result


def role_for(cursor, user_id):
    cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise APIError("Login first.", 401)
    return user["role"]
