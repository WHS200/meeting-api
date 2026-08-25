from flask import Blueprint, session

from werkzeug.security import check_password_hash, generate_password_hash

from app.shared.database import get_db_connection
from app.shared.decorators import login_required
from app.shared.request_utils import get_json_body

# /api/users 용
users_bp = Blueprint("users", __name__, url_prefix="/api/users")

# 내 프로필 조회
@users_bp.get("/me")
@login_required
def get_me():
    user_id = session.get("user_id")

    # DB 연결
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 사용자 정보 조회
    try:
        cursor.execute(
            """
            SELECT login_id, nickname, email, profile_image, birth_date, gender, region
            FROM users
            WHERE status != 'DELETED' AND user_id = %s
            """,
            (user_id,)
        )
        user_info = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if not user_info:
        session.clear()
        return {"message": "User not found."}, 401

    return user_info, 200

# 내 정보 수정
@users_bp.patch("/me")
@login_required
def update_me():
    user_id = session.get("user_id")

    user_info, error = get_json_body()

    if error:
        return error

    # 수정 가능한 필드
    allowed_fields = ["nickname", "region"]

    # nickname, region 둘 다 안 보냈으면
    if not any(key in user_info for key in allowed_fields):  # allowed_fields의 각 key에 대해, 그 key가 user_info 안에 있는지를 하나씩 검사
        return {"message": "Change nickname or region."}, 400

    # 보낸 필드만 검사
    for key in allowed_fields:
        if key in user_info:
            value = user_info.get(key)

            if not value:
                return {"message": f"input {key}."}, 400

            if not isinstance(value, str):
                return {"message": f"{key} must be string type."}, 400

    # 변수 설정
    nickname = user_info.get("nickname")
    region = user_info.get("region")

    # DB 연결
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # nickname 입력됐으면
        if nickname:
        # 중복 검사
            cursor.execute("SELECT 1 FROM users WHERE user_id != %s AND nickname = %s", (user_id, nickname))
            if cursor.fetchone():
                return {"message": "nickname already exists."}, 409

            # 중복 검사 통과 후 커밋
            cursor.execute(
                """
                UPDATE users
                SET nickname = %s
                WHERE status != 'DELETED' AND user_id = %s
                """, (nickname, user_id)
            )

        # region 입력됐으면
        if region:
            cursor.execute(
                """
                UPDATE users
                SET region = %s
                WHERE status != 'DELETED' AND user_id = %s
                """, (region, user_id)
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return {"message": "Updated successfully."}, 200

# 계정 삭제

@users_bp.delete("/me")
@login_required
def delete_me():
    user_id = session.get("user_id")

    deleted_login_id = f"deleted_user_{user_id}"
    deleted_nickname = f"deleted_user_{user_id}"
    deleted_email = f"deleted_user_{user_id}@deleted.local"

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 이미 삭제된 계정인지 확인
        cursor.execute(
            """
            SELECT 1
            FROM users
            WHERE status = 'DELETED'
            AND user_id = %s
            """,
            (user_id,)
        )

        if cursor.fetchone():
            return {"message": "Already deleted."}, 400

        # soft delete
        cursor.execute(
            """
            UPDATE users
            SET login_id = %s,
                nickname = %s,
                email = %s,
                status = 'DELETED'
            WHERE user_id = %s
            """,
            (
                deleted_login_id,
                deleted_nickname,
                deleted_email,
                user_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    session.clear()

    return {"message": "Deleted successfully."}, 200


# 상대 프로필 조회
@users_bp.get("/<int:user_id>")
@login_required
def get_user_profile(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 상대 기본 정보 조회
        cursor.execute(
            """
            SELECT nickname, profile_image, region
            FROM users
            WHERE user_id = %s
            AND status != 'DELETED'
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:
            return {
                "message": "User not found."
            }, 404

        # 상대 운동 목록 조회
        cursor.execute(
            """
            SELECT
                s.sport_id,
                s.sport_name,
                us.skill_level
            FROM sports AS s
            JOIN user_sports AS us
                ON s.sport_id = us.sport_id
            WHERE us.user_id = %s
            """,
            (user_id,)
        )

        sports = cursor.fetchall()

        # 반환할 사용자 정보에 sports 추가
        user["sports"] = sports

    finally:
        cursor.close()
        connection.close()

    return user, 200


# 비밀번호 변경
@users_bp.patch("/me/password")
@login_required
def update_password():
    user_id = session.get("user_id")

    password_data, error = get_json_body(
        ["current_password", "new_password"]
    )

    if error:
        return error

    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")

    # 새 비밀번호는 최소 8자
    if len(new_password) < 8:
        return {"message": "New password must be at least 8 characters."}, 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 현재 비밀번호 hash 조회
        cursor.execute(
            """
            SELECT password
            FROM users
            WHERE user_id = %s
            AND status != 'DELETED'
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        # 세션은 있는데 유효한 사용자가 없으면
        if not user:
            session.clear()
            return {"message": "Login first."}, 401

        password_hash = user.get("password")

        # 현재 비밀번호 확인
        if not check_password_hash(password_hash, current_password):
            return {"message": "Current password is incorrect."}, 401

        # 새 비밀번호 hashing
        new_password_hash = generate_password_hash(new_password)

        # 새 비밀번호 저장
        cursor.execute(
            """
            UPDATE users
            SET password = %s
            WHERE user_id = %s
            AND status != 'DELETED'
            """,
            (new_password_hash, user_id)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return {"message": "Password updated successfully."}, 200
