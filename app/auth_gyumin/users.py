from flask import Blueprint, session, request

users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users"
)

def check_session():
    user_info["user_id"] = session["user_id"]


@users_bp.get("/me")
def get_me():
    pass