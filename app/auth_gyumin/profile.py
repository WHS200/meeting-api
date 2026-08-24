import os

from flask import Blueprint, session, request, send_from_directory, current_app
from uuid import uuid4

from app.auth_gyumin.users import users_bp
from app.shared.database import get_db_connection
from app.shared.decorators import login_required

uploads_bp = Blueprint("uploads", __name__)

# 프로필 이미지 등록 / 변경
@users_bp.post("/me/profile-image")
@login_required
def upload_profile_image():
    user_id = session.get("user_id")

    # multipart/form-data의 파일 가져오기
    file = request.files.get("profile_image")

    if not file:
        return {"message": "Profile image is required."}, 400

    filename = file.filename or ""

    # 확장자가 없는 파일 거부
    if "." not in filename:
        return {"message": "Invalid image file."}, 400

    extension = filename.rsplit(".", 1)[1].lower()

    # 허용 확장자
    if extension not in ("jpg", "jpeg", "png", "webp"):
        return {"message": "Invalid image file."}, 400

    # Content-Type 확인
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        return {"message": "Invalid image content type."}, 400

    # 파일 저장 폴더
    profile_upload_folder = os.path.join(
        current_app.root_path, "uploads", "profile"
    )

    # 폴더가 없으면 생성
    os.makedirs(profile_upload_folder, exist_ok=True)

    # 원래 filename 대신 UUID 사용
    stored_filename = f"{uuid4().hex}.{extension}"

    save_path = os.path.join(profile_upload_folder, stored_filename)

    file.save(save_path)

    # DB에는 파일 경로 저장
    profile_image_path = f"/uploads/profile/{stored_filename}"

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE users
            SET profile_image = %s
            WHERE user_id = %s
            AND status != 'DELETED'
            """,
            (profile_image_path, user_id)
        )

        connection.commit()

    except Exception:
        connection.rollback()

        # DB 저장 실패하면 방금 저장한 파일 제거
        if os.path.exists(save_path):
            os.remove(save_path)

        raise

    finally:
        cursor.close()
        connection.close()

    return {
        "message": "Profile image updated successfully.",
        "profile_image": profile_image_path
    }, 200

# 프로필 이미지 파일 조회
@uploads_bp.get("/uploads/profile/<filename>")
def get_profile_image(filename):
    profile_upload_folder = os.path.join(
        current_app.root_path, "uploads", "profile"
    )

    return send_from_directory(profile_upload_folder, filename)
