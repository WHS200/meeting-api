# 모임 CRUD / 검색

- 담당자: 규동
- 작업 브랜치: `feature/gyudong-meetings`
- 주요 주제: REST, CRUD, SQL, JOIN, 필터링

## 파일

- `meetings.py`: Blueprint 기반 모임 CRUD·검색 API
- `meetings.sql`: MySQL `meetings` 테이블 생성 SQL

## Blueprint 등록

공통 `app.py` 담당자가 아래 내용을 등록해야 API가 활성화됩니다.

```python
from app.meetings_gyudong.meetings import meetings_bp

app.register_blueprint(meetings_bp)
```

## API

| Method | URL | 설명 | 로그인 |
| --- | --- | --- | --- |
| GET | `/api/meetings` | 목록·검색·필터링 | 불필요 |
| GET | `/api/meetings/<meeting_id>` | 상세 조회 | 불필요 |
| POST | `/api/meetings` | 모임 생성 | 필요 |
| PUT | `/api/meetings/<meeting_id>` | 모임 전체 수정 | 필요 |
| DELETE | `/api/meetings/<meeting_id>` | 모임 삭제 | 필요 |
| GET | `/api/meetings/mine` | 내가 만든 모임 조회 | 필요 |

목록 API는 `keyword`, `sport_id`, `date`, `location`, `status` 쿼리 파라미터를 지원합니다.
