import os

import boto3


S3_REGION = "ap-northeast-2"

# Python에서 S3를 사용할 객체 생성
def get_s3_client():
    # boto3.client("S3") => S3 API를 호출할 수 있는 객체 하나 생성
    return boto3.client(
        "s3", # EC2에 IAM Role을 붙여놨기 때문에 boto3.client("s3")만으로 인증 가능
        region_name=S3_REGION
    )


def get_s3_bucket_name():
    bucket_name = os.getenv("S3_BUCKET_NAME") # Docker가 전달한 yanawa-profile 값을 읽음

    if not bucket_name:
        raise RuntimeError(
            "S3_BUCKET_NAME environment variable is not set."
        )

    return bucket_name

# DB의 S3 key를 브라우저에서 볼 수 있는 URL로 변환
def generate_profile_image_url(profile_image):
    if not profile_image:
        return None

    # 기존 로컬 방식의 프로필 이미지는 그대로 사용
    if profile_image.startswith("/uploads/"):
        return profile_image

    # S3 프로필 이미지가 아니면 그대로 반환
    if not profile_image.startswith("profile/"):
        return profile_image

    s3 = get_s3_client()
    bucket_name = get_s3_bucket_name()

    return s3.generate_presigned_url( # S3의 private 파일에 임시 접근 URL 생성
        "get_object", # S3 파일을 읽는 작업
        Params={
            "Bucket": bucket_name,
            "Key": profile_image,
        },
        ExpiresIn=3600,
    )