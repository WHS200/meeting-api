from flask import Blueprint, session

from app.auth_gyumin.users import users_bp
from app.shared.database import get_db_connection
from app.shared.decorators import login_required
from app.shared.request_utils import get_json_body

sports_bp = Blueprint("sports", __name__, url_prefix="/api")

# 내 운동 프로필 조회
@users_bp.get("/me/sports")
@login_required
def get_my_sports():
    user_id = session.get("user_id")

    # DB 연결
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                s.sport_id,
                s.sport_name,
                us.skill_level
            FROM user_sports AS us
            JOIN sports AS s
                ON us.sport_id = s.sport_id
            WHERE us.user_id = %s
            """,
            (user_id,)
        )

        my_sports_list = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return {"sports": my_sports_list}, 200

# 내 운동 종목 추가
@users_bp.post("/me/sports")
@login_required
def add_my_sport():
    user_id = session.get("user_id")

    input_sport, error = get_json_body()

    if error:
        return error

    # sport_id와 skill_level 둘 다 필요
    if "sport_id" not in input_sport or "skill_level" not in input_sport:
        return {"message": "Need to input sport_id and skill_level."}, 400

    sport_id = input_sport.get("sport_id")
    skill_level = input_sport.get("skill_level")

    # sport_id는 정수
    if isinstance(sport_id, bool) or not isinstance(sport_id, int):
        return {"message": "sport_id must be integer type."}, 400

    # skill_level은 문자열
    if not isinstance(skill_level, str):
        return {"message": "skill_level must be string type."}, 400

    # 실력 값 검증
    if skill_level not in ("BRONZE", "SILVER", "GOLD", "MASTER"):
        return {
            "message": "skill_level must be BRONZE, SILVER, GOLD, or MASTER."
        }, 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 실제 존재하는 활성화된 운동인지 확인
        cursor.execute(
            """
            SELECT 1
            FROM sports
            WHERE sport_id = %s
            AND status = 'ACTIVE'
            """,
            (sport_id,)
        )

        if not cursor.fetchone():
            return {"message": "Sport not found."}, 404

        # 이미 등록한 종목인지 확인
        cursor.execute(
            """
            SELECT 1
            FROM user_sports
            WHERE user_id = %s
            AND sport_id = %s
            """,
            (user_id, sport_id)
        )

        if cursor.fetchone():
            return {"message": "You already registered this sport."}, 409

        # 운동 프로필 추가
        cursor.execute(
            """
            INSERT INTO user_sports (
                user_id,
                sport_id,
                skill_level
            )
            VALUES (%s, %s, %s)
            """,
            (user_id, sport_id, skill_level)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return {"message": "Sport registered successfully."}, 201

# 내 운동 실력 수정
@users_bp.patch("/me/sports/<int:sport_id>")
@login_required
def update_my_sport(sport_id):
    user_id = session.get("user_id")

    sport_info, error = get_json_body(["skill_level"])

    if error:
        return error

    skill_level = sport_info.get("skill_level")

    if skill_level not in ("BRONZE", "SILVER", "GOLD", "MASTER"):
        return {
            "message": "skill_level must be BRONZE, SILVER, GOLD, or MASTER."
        }, 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 내가 등록한 종목인지 확인
        cursor.execute(
            """
            SELECT 1
            FROM user_sports
            WHERE user_id = %s
            AND sport_id = %s
            """,
            (user_id, sport_id)
        )

        if not cursor.fetchone():
            return {"message": "Register sport first."}, 404

        # 실력 수정
        cursor.execute(
            """
            UPDATE user_sports
            SET skill_level = %s
            WHERE user_id = %s
            AND sport_id = %s
            """,
            (skill_level, user_id, sport_id)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return {"message": "Sport updated successfully."}, 200

# 내 운동 종목 삭제
@users_bp.delete("/me/sports/<int:sport_id>")
@login_required
def delete_my_sport(sport_id):
    user_id = session.get("user_id")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 내가 등록한 종목인지 확인
        cursor.execute(
            """
            SELECT 1
            FROM user_sports
            WHERE user_id = %s
            AND sport_id = %s
            """,
            (user_id, sport_id)
        )

        if not cursor.fetchone():
            return {"message": "Sport not registered."}, 404

        # 삭제
        cursor.execute(
            """
            DELETE FROM user_sports
            WHERE user_id = %s
            AND sport_id = %s
            """,
            (user_id, sport_id)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return {"message": "Sport deleted successfully."}, 200

# 전체 운동 종목 조회
@sports_bp.get("/sports")
def get_sports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT sport_id, sport_name
            FROM sports
            WHERE status = 'ACTIVE'
            """
        )

        sports_list = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return sports_list, 200
