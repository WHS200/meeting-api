from flask import Blueprint, request, session
from werkzeug.security import check_password_hash

from app.shared.database import get_db_connection


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth"
)


@auth_bp.get("/test")
def auth_test():
    return {
        "message": "auth blueprint works"
    }, 200


@auth_bp.post("/login")
def login():

    if not request.is_json:
        return {
            "message": "Content-Type must be application/json"
        }, 415

    data = request.get_json()

    if not isinstance(data, dict):
        return {
            "message": "JSON body must be an object"
        }, 400

    login_id = data.get("login_id")
    password = data.get("password")

    if not login_id or not password:
        return {
            "message": "need login_id and password"
        }, 400

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE login_id = %s
        """,
        (login_id,)
    )

    user = cursor.fetchone()

    connection.close()

    if not user:
        return {
            "message": "Invalid login id or password"
        }, 401

    if user["status"] == "DELETED":
        return {
            "message": "Invalid login id or password"
        }, 401

    if not check_password_hash(
        user["password"],
        password
    ):
        return {
            "message": "Invalid login id or password"
        }, 401

    session["user_id"] = user["user_id"]

    return {
        "message": "login successful"
    }, 200