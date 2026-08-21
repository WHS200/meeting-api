# Meeting API

팀원 4명이 하나의 저장소에서 기능 브랜치로 협업하는 프로젝트입니다.

## 담당 영역

| 담당자 | 작업 브랜치 | 코드 영역 | 담당 기능 |
| --- | --- | --- | --- |
| 규민 | `feature/gyumin-auth` | `app/auth/` | 인증, 사용자, 프로필 |
| 규동 | `feature/gyudong-meetings` | `app/meetings/` | 모임 CRUD, 검색 |
| 은아 | `feature/euna-participation` | `app/participation/` | 참여, 승인, 강퇴, 출석 |
| 다현 | `feature/dahyun-chat` | `app/chat/` | 채팅, WebSocket |

공통 코드는 `app/shared/`에 작성합니다. 완성된 기능은 각 작업 브랜치에서
`main`을 대상으로 Pull Request를 생성하고, 다른 팀원의 리뷰를 받은 뒤 병합합니다.

## 현재 코드

`meeting_api_demo.py`와 `test_meeting_api.py`는 모임 CRUD 기능의 초기 실행 예제입니다.
기능을 모듈화할 때 `app/meetings/`와 `tests/`로 나누어 이동할 예정입니다.

## 기본 작업 순서

```bash
git switch main
git pull origin main
git switch feature/본인-브랜치
git merge main

# 코드 수정 후
git add -- 수정한파일
git commit -m "feat: 작업 내용"
git push origin feature/본인-브랜치
```

그다음 GitHub에서 작업 브랜치를 `main`으로 보내는 Pull Request를 생성합니다.
