from functools import wraps

from flask import session


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            return {"message": "Login first."}, 401

        return func(*args, **kwargs)

    return wrapper
