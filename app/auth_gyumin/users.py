from flask import Blueprint


users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users"
)


@users_bp.get("/test")
def users_test():
    return {
        "message": "users blueprint works"
    }, 200