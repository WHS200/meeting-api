import json

from meeting_api_demo import create_app


app = create_app()
ctx = app.app_context()
ctx.push()
app.init_db()
client = app.test_client()


def login(user_id=1):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def show(number, name, method, url, **kwargs):
    response = client.open(url, method=method, **kwargs)
    body = response.get_json(silent=True)
    print(f"[{number}] {name}")
    print(f"{method} {url}")
    print(f"STATUS {response.status_code}")
    print(json.dumps(body, ensure_ascii=False, indent=2) if body is not None else "(응답 본문 없음)")
    print()
    return response


show(1, "모임 목록 조회", "GET", "/api/meetings")
show(2, "모임 상세 조회", "GET", "/api/meetings/1")

login(1)
created = show(
    3,
    "모임 생성",
    "POST",
    "/api/meetings",
    json={
        "title": "아침 공원 러닝",
        "description": "가볍게 5km를 달립니다.",
        "sport_id": 1,
        "meeting_date": "2026-08-30",
        "location": "서울숲",
        "max_members": 8,
    },
)
new_id = created.get_json()["meeting_id"]

show(
    4,
    "모임 전체 수정",
    "PUT",
    f"/api/meetings/{new_id}",
    json={
        "title": "아침 서울숲 러닝",
        "description": "가볍게 7km를 달립니다.",
        "sport_id": 1,
        "meeting_date": "2026-08-31",
        "location": "서울숲 입구",
        "max_members": 10,
        "status": "RECRUITING",
    },
)

show(6, "모임 검색", "GET", "/api/meetings?keyword=한강")
show(7, "운동 종목 필터링", "GET", "/api/meetings?sport_id=1")
show(8, "날짜 필터링", "GET", "/api/meetings?date=2026-08-22")
show(9, "지역 필터링", "GET", "/api/meetings?location=강남")
show(10, "모집 상태 필터링", "GET", "/api/meetings?status=RECRUITING")
show(11, "복합 검색 및 필터링", "GET", "/api/meetings?keyword=한강&sport_id=1&date=2026-08-22")
show(12, "내가 만든 모임 조회", "GET", "/api/users/me/meetings")
show(5, "모임 삭제", "DELETE", f"/api/meetings/{new_id}")
show("5-확인", "삭제 결과 확인", "GET", f"/api/meetings/{new_id}")

ctx.pop()
