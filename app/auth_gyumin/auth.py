import re
from datetime import datetime

from flask import Blueprint, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.shared.database import get_db_connection

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth"
)

# 안전한 JSON 형식인지 확인
def get_json_body(required_fields=None):
    # 1. JSON 요청인지 확인
    if not request.is_json:
        return None, ({"message": "Content-Type should be JSON."}, 415)

    # 2. JSON body 가져오기
    data = request.get_json()

    # 3. JSON object(dict)인지 확인
    if not isinstance(data, dict):
        return None, ({"message": "Format should be dictionary."}, 400)

    # 4. 필수 필드 검사
    if required_fields:
        for key in required_fields:
            value = data.get(key)

            if not value:
                return None, ({"message": f"input {key}."}, 400)

            if not isinstance(value, str):
                return None, ({"message": f"{key} must be string type."}, 400)
            
    return data, None

# 회원가입 
@auth_bp.post("/signup")
def signup():
    # 올바른 형식이면 user_info = data, error = None
    # 아니면 user_info = None, error = 에러메시지, 에러코드
    user_info, error = get_json_body(
        [
            "login_id",
            "password",
            "nickname",
            "email",
            "birth_date",
            "region",
            "gender"
        ]
    )

    if error:
        return error
    
    
    # 입력받은 값 변수로 저장
    login_id = user_info.get("login_id")
    password = user_info.get("password")
    nickname = user_info.get("nickname")
    email = user_info.get("email")
    birth_date = user_info.get("birth_date")
    region = user_info.get("region")
    gender = user_info.get("gender")

    ## 값 형식 검사
    # 비밀번호가 8자리 이상인지 확인
    if len(password) < 8:
        return {"message": "password length must be at least 8 characters."}, 400
    # 이메일 형식 확인
    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_pattern, email):
        return {"message": "that's not the email format."}, 400
    # 날짜 형식 확인
    try:
        datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        return {"message": "birth date type should be YYYY-MM-DD."}, 400
    # 성별 입력 확인
    if gender not in ("MALE", "FEMALE"):
        return {"message": "gender must be MALE or FEMALE."}, 400
    # 삭제된 사용자와 충돌되지 않게
    if login_id.startswith("deleted_user_"):
        return {"message": "This login ID prefix is reserved."}, 400


    # DB 연결
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 중간에 return 시 db 닫기 위해 try, finally 사용
    try: 
        ## DB 중복 검사
        # 아이디 중복 확인
        cursor.execute("SELECT user_id FROM users Where login_id = %s", (login_id, ))
        existing_login_id = cursor.fetchone()
        if existing_login_id:
            return {"message": "Existing ID."}, 409
        # email 중복 확인
        cursor.execute("SELECT email FROM users where email = %s", (email, ))
        existing_email = cursor.fetchone()
        if existing_email:
            return {"message": "Existing Email."}, 409
        # nickname 중복 확인
        cursor.execute("SELECT nickname FROM users WHERE nickname = %s", (nickname, ))
        existing_nickname = cursor.fetchone()
        if existing_nickname:
            return {"message": "Existing nickname."}, 409


        ## DB에 Commit
        # 비밀번호 hash로 저장
        password_hash = generate_password_hash(password)
        # Commit: 지금까지의 변경을 확정
        cursor.execute(
        "INSERT into users (login_id, password, nickname, email, birth_date, gender, region) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (login_id, password_hash, nickname, email, birth_date, gender, region)
        )
        connection.commit()

    # DB 오류 시 rollback: 아직 확정(commit)되지 않은 변경사항을 취소
    except Exception:
        connection.rollback() 
        raise 
    # 원래 DB 오류를 Flask로 다시 전달
    # -> Flask 콘솔에 traceback
    # -> 500 Internal Server Error
    # -> finally 실행해서 DB 연결 닫음

    finally:
        # DB 연결 해제
        cursor.close()
        connection.close()


    return {"message": "registered."}, 201    

# 로그인
@auth_bp.post("/login")
def login():
    user_info, error = get_json_body(
        [
            "login_id",
            "password"
        ]
    )

    if error:
        return error

    # 변수 받아오기
    login_id = user_info.get("login_id")
    password = user_info.get("password")

    # DB 연결
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 존재하는 사용자인지 확인
        cursor.execute("SELECT user_id, password FROM users WHERE status != 'DELETED' AND login_id = %s", (login_id, ))
        existing_user = cursor.fetchone()
        if not existing_user:
            return {"message": "Wrong ID or Password."}, 401

        # 비밀번호 일치 확인
        password_hash = existing_user.get("password")
        if not check_password_hash(password_hash, password):
            return {"message": "Wrong ID or Password."}, 401

        # 로그인 성공 (DB에서 조회한 user_id를 세션에 저장)
        session.clear()
        session["user_id"] = existing_user["user_id"]
    finally:
        cursor.close()
        connection.close()

    return {"message": "Login Success."}, 200

# 로그아웃
@auth_bp.post("/logout")
def logout():
    session.clear()

    return {"message": "Logout success."}, 200