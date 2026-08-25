from flask import request

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