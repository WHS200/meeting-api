from functools import wraps

from flask import session

# func => 데코레이터가 붙은 원래 함수
# e.g.
# @login_required
# def get_me():
# ... 이면
# get_me = login_required(get_me)
def login_required(func):
    @wraps(func) # = 원래 함수 정보를 유지해주는 장치

    # wrapper: 원래 함수를 감싸는 새 함수
    # 원래 get_me()만 실행하던 것을 =>
    # wrapper() ->
    # 로그인 검사 ->
    # get_me()로 바꾸는 것
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            return {"message": "Login first."}, 401

        return func(*args, **kwargs)
        # 로그인이 확인돼었으니 원래 실행하려던 함수를 이제 실행하라.

    return wrapper

# *args, **kwargs?
# 원래 함수가 어떤 인자를 받든 그대로 넘겨주기 위해 사용
