import os
import boto3 # AWS를 사용하기 위한 라이브러리

from flask import Blueprint, session, request, send_from_directory, current_app
from uuid import uuid4

from app.auth_gyumin.users import users_bp
from app.shared.database import get_db_connection
from app.shared.decorators import login_required

# 프로필 이미지 등록 / 변경
@users_bp.post("/me/profile-image")
@login_required
def upload_profile_image():
    user_id = session.get("user_id")

    # 1. 프론트가 보낸 이미지 받기
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

    # =================test=======================
    # 파일 저장 폴더
    # profile_upload_folder = os.path.join(
    #     current_app.root_path, "uploads", "profile"
    # )

    # # 폴더가 없으면 생성
    # os.makedirs(profile_upload_folder, exist_ok=True)

    # # 원래 filename 대신 UUID 사용
    # stored_filename = f"{uuid4().hex}.{extension}"

    # save_path = os.path.join(profile_upload_folder, stored_filename)

    # file.save(save_path)
    #==================================================
    
    # 2. S3 연결
    s3 = boto3.client("s3") # S3 사용

    bucket_name = os.getenv("S3_BUCKET_NAME") # S3 파일 저장소 이름 정의
#  <AWS S3>
# yanawa-profile        ← 버킷
# └── profile
#     ├── abc123.jpg
#     └── def456.png

    # 3. 랜덤 파일 이름 생성
    stored_filename = f"{uuid4().hex}.{extension}"

    s3_key = f"profile/{stored_filename}" # S3 안에서 저장할 위치

    # 4. S3에 이미지 저장
    s3.upload_fileobj( # 사용자가 보내준 파일은 bucket_name이라는 S3 저장소의 s3_key 위치에 저장
        file.stream,
        bucket_name,
        s3_key,
        ExtraArgs={
            "ContentType": file.content_type
        }
    )

    # 5. DB에는 이미지 자체가 아닌 S3 위치만 저장
    profile_image_path = s3_key

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

        # DB 저장 실패하면 S3에 올렸던 이미지 삭제
        s3.delete_object(
            Bucket=bucket_name,
            Key=s3_key
        )

        raise

    finally:
        cursor.close()
        connection.close()

    return {
        "message": "Profile image updated successfully.",
        "profile_image": profile_image_path
    }, 200
