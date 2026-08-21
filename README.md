# Meeting API

팀원 4명이 하나의 저장소에서 기능 브랜치로 협업하는 프로젝트입니다.

## 담당 영역

| 담당자 | 작업 브랜치 | 코드 영역 | 담당 기능 |
| --- | --- | --- | --- |
| 규민 | `feature/gyumin-auth` | `app/auth_gyumin/` | 인증, 사용자, 프로필 |
| 규동 | `feature/gyudong-meetings` | `app/meetings_gyudong/` | 모임 CRUD, 검색 |
| 은아 | `feature/euna-participation` | `app/participation_euna/` | 참여, 승인, 강퇴, 출석 |
| 다현 | `feature/dahyun-chat` | `app/chat_dahyun/` | 채팅, WebSocket |

공통 코드는 `app/shared/`에 작성합니다.

## 공통 규칙

```text
로그인 성공
→ session["user_id"] 존재

로그인 안 됨
→ session.get("user_id") is None

관리자 여부
→ users.role == "ADMIN"

datetime → %Y-%m-%d (4자리 연도 - 월 - 일)
```
