import os
from uuid import uuid4

from flask import (Blueprint, current_app, request, send_from_directory, session,)

from app.auth_gyumin.users import users_bp
from app.shared.database import get_db_connection
from app.shared.decorators import login_required
from app.shared.s3 import (
    generate_profile_image_url,
    get_s3_bucket_name,
    get_s3_client,
)


uploads_bp = Blueprint("uploads", __name__)


# 프로필 이미지 등록 / 변경
@users_bp.post("/me/profile-image")
@login_required
def upload_profile_image():
    user_id = session.get("user_id")

    # multipart/form-data로 전달된 이미지 파일
    file = request.files.get("profile_image")

    if not file:
        return {"message": "Profile image is required."}, 400

    filename = file.filename or ""

    # 확장자가 없는 파일 거부
    if "." not in filename:
        return {"message": "Invalid image file."}, 400

    extension = filename.rsplit(".", 1)[1].lower()

    # 허용할 확장자
    if extension not in ("jpg", "jpeg", "png", "webp",):
        return {"message": "Invalid image file."}, 400

    # MIME Content-Type 확인
    if file.content_type not in ("image/jpeg", "image/png", "image/webp",):
        return {"message": "Invalid image content type."}, 400

    s3 = get_s3_client()
    bucket_name = get_s3_bucket_name()

    # 같은 파일명이 충돌하지 않도록 UUID 사용
    stored_filename = (f"{uuid4().hex}.{extension}")

    # S3 내부 파일 경로
    s3_key = (f"profile/{stored_filename}")

    # S3에 이미지 업로드
    s3.upload_fileobj(
        file.stream, # 사용자가 업로드한 실제 이미지 데이터
        bucket_name, # yanawa-profile
        s3_key, # profile/랜덤UUID.png
        ExtraArgs={"ContentType": file.content_type} # 이 파일이 image/png 같은 이미지라는 메타 정보
    )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    old_profile_image = None

    try:
        # 기존 프로필 이미지 확인
        cursor.execute(
            """
            SELECT profile_image
            FROM users
            WHERE user_id = %s
            AND status != 'DELETED'
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:
            # 유효한 사용자가 아니라면
            # 방금 올린 S3 파일 제거
            s3.delete_object(Bucket=bucket_name, Key=s3_key)

            session.clear()

            return {"message": "User not found."}, 401

        old_profile_image = (user.get("profile_image"))

        # DB에는 URL이 아니라 S3 key만 저장
        cursor.execute(
            """
            UPDATE users
            SET profile_image = %s
            WHERE user_id = %s
            AND status != 'DELETED'
            """,
            (s3_key, user_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()

        # DB 저장 실패 시
        # 새로 업로드한 S3 파일 제거
        s3.delete_object(Bucket=bucket_name, Key=s3_key)

        raise

    finally:
        cursor.close()
        connection.close()

    # 기존 프로필도 S3 파일이었다면 제거
    if (
        old_profile_image
        and old_profile_image.startswith("profile/")
        and old_profile_image != s3_key
    ):
        try:
            s3.delete_object(Bucket=bucket_name, Key=old_profile_image)
        except Exception:
            # 새 프로필 저장 자체는 성공했으므로
            # 기존 파일 삭제 실패로 요청 전체를 실패시키지 않음
            pass

    return {
        "message": "Profile image updated successfully.",
        "profile_image": generate_profile_image_url(s3_key)
    }, 200


# 기존 로컬 이미지 호환용
@uploads_bp.get("/uploads/profile/<filename>")
def get_profile_image(filename):
    profile_upload_folder = os.path.join(current_app.root_path, "uploads", "profile")

    return send_from_directory(profile_upload_folder, filename)
