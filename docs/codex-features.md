# YANAWA Codex 확장 기능

분석·구현 기준은 WHS200/meeting-api main `376101825cd6cdf7870ec41a7051bc341af898f4`이다.
기존 Flask session, `session["user_id"]`, `login_required`, DB connection, S3 URL 변환,
Blueprint 및 `%s` parameter binding을 그대로 사용한다.

## 1. 추가·수정 파일

- `app/codex_features/`: 친구, 차단, 개인톡, 커뮤니티, 신고, 관리자, 알림,
  관심 모임, 프로필 통계, 대기자, 종목 관리와 공통 helper.
- 기존 연결부: `server.py`, `auth_gyumin/auth.py`, `auth_gyumin/users.py`,
  `chat_dahyun/socket_events.py`, `meetings_gyudong/meetings.py`,
  `participation_euna/helpers.py`, `participation_euna/participation.py`.
- `database/init.sql`, `database/migrations/002_*.sql`~`010_*.sql`,
  `database/migrate.py`.
- 신규 화면: `friends.html`, `community.html`, `post-detail.html`,
  `reports.html`, `notifications.html`, `favorites.html`, `sports.html`,
  `static/admin/*.html`. 기존 프로필·모임·채팅 화면에는 작은 연결 script만 추가.
- 테스트: `test_social.py`, `test_direct_chat.py`, `test_community.py`,
  `test_reports.py`, `test_admin.py`, `test_notifications.py`,
  `test_favorites_stats.py`, `test_waitlist_schedule.py`,
  `test_sports_management.py`, `test_migrations.py`.

사용자가 작업 전에 수정해 둔 `requirements.txt` 내용은 보존했다.

## 2. DB schema 변경

| migration | 변경 |
|---|---|
| 002_social | friend_requests, friendships, user_blocks. 정렬된 사용자 쌍과 pending generated key로 양방향 중복 방지 |
| 003_direct_chat | chat_rooms.direct_low/direct_high, DIRECT 사용자 쌍 UNIQUE/CHECK/FK |
| 004_community | community_posts, community_comments, soft delete, 길이 CHECK |
| 005_reports | reports, 대상별 nullable FK, 처리자·시각·메모, 제한 조회 index |
| 006_admin | users 정지 종료·사유, meetings 관리 사유, admin_actions |
| 007_notifications | notifications 및 inbox/unread index |
| 008_favorites | meeting_favorites 복합 PK/FK |
| 009_meeting_extensions | meetings.end_time, WAITING/waiting_at, 일정·대기 index, DB mutex row |
| 010_sports_management | sport_proposals, sports.merged_into, 종목 mutex row |

신규 DB는 `init.sql`로 최종 구조가 만들어진다. 기존 volume은 migration을 적용해야 한다.

## 3. migration 적용 방법

배포 전에 DB 백업을 만들고 다음 preflight를 확인한다.

```sql
SELECT meeting_id, meeting_date, meeting_time
FROM meetings WHERE meeting_time > '23:29:59';

SELECT REGEXP_REPLACE(TRIM(sport_name), '[[:space:]]+', ' ') AS normalized_name,
       COUNT(*) AS count
FROM sports GROUP BY normalized_name HAVING count > 1;
```

첫 조회 결과는 같은 날짜 안에 30분짜리 `end_time`을 만들 수 있도록 시작시간을 먼저
수정해야 한다. 두 번째 결과는 종목 이름을 병합하거나 이름을 먼저 정리해야 한다.
`database/migrate.py`도 이 조건을 검사하고 안전하지 않으면 중단한다.

EC2 저장소에서 현재 환경 변수가 들어 있는 `.env`와 새 app image를 기준으로 실행한다.

```bash
docker compose stop app
docker compose build app
docker compose run --rm app python database/migrate.py
docker compose run --rm app python database/migrate.py --check
docker compose up -d app
```

실행기는 `schema_migrations`와 checksum을 기록하고 동시 실행 lock을 잡는다. 최신 main에
이미 포함된 001 컬럼은 자동 baseline 처리한다. MySQL DDL은 migration 파일 전체가 하나의
트랜잭션으로 rollback되지 않으므로 백업은 필수다. 실패 시 원인을 고친 뒤 적용된 DDL과
`schema_migrations` 상태를 확인하고 재실행한다.

## 4. 추가·확장 API와 5. 인증/권한

모든 변경 API는 body의 user ID를 로그인 신원으로 사용하지 않는다. `본인`은 항상 session
user ID다. 목록은 기본 30건이며 `limit`(1~100), `offset`을 지원한다.

| 영역 | API | 정책 |
|---|---|---|
| 친구 | `GET /api/friends/search?nickname=`, `GET /api/friends`, `GET /api/friends/requests?direction=received|sent` | 로그인 |
| 친구 | `POST /api/friends/requests`, `POST /api/friends/requests/{id}/accept|reject|cancel`, `DELETE /api/friends/{user_id}` | 로그인, 수신자/발신자/관계 당사자 검사 |
| 차단 | `GET /api/blocks`, `POST/DELETE /api/blocks/{user_id}` | 로그인, 차단 생성자만 해제 |
| 개인톡 | `POST /api/chat/direct` | 로그인, 차단 관계 금지, 정렬된 쌍 UNIQUE |
| 기존 채팅 확장 | `GET /api/chat/rooms/{id}/messages|members`, Socket.IO `join_room/send_message` | room member만, DIRECT 송신 때 차단 재검사 |
| 커뮤니티 | `GET /api/community/posts`, `GET /api/community/posts/{id}` | 로그인 |
| 커뮤니티 | `POST/PUT/DELETE /api/community/posts[/{id}]`, `POST /api/community/posts/{id}/comments`, `DELETE /api/community/comments/{id}` | 작성자 또는 ADMIN, NOTICE 작성·편집은 ADMIN |
| 신고 | `POST /api/reports`, `GET /api/reports/mine` | 로그인, 자기 USER/POST 금지, 일 10건·대상 24시간 제한 |
| 알림 | `GET /api/notifications`, `GET /api/notifications/unread-count`, `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all` | 로그인, session 소유 알림만 변경 |
| 관심 | `GET /api/favorites`, `POST/DELETE /api/favorites/{meeting_id}` | 로그인, 복합 PK 중복 방지 |
| 통계 | `GET /api/users/me/stats`, `GET /api/users/{user_id}/stats` | 로그인, 기존 데이터 집계 |
| 대기 | `GET /api/meetings/{meeting_id}/waitlist` | 로그인, 본인은 자기 순위만, host는 전체 |
| 모임 확장 | 기존 모임 생성·수정 body에 `end_time`; 기존 참가·승인·취소·강퇴에 WAITING/승급 | 로그인, host/본인 기존 권한 유지, 일정·정원 DB lock |
| 종목 | `POST /api/sports/proposals`, `GET /api/sports/proposals/mine` | 로그인, UTC 하루 5개, 상태 변경 불가 |
| 관리자 | `GET /api/admin/users[/{id}]`, `POST /api/admin/users/{id}/suspend|unsuspend` | ADMIN |
| 관리자 | `GET /api/admin/meetings`, `POST /api/admin/meetings/{id}/cancel` | ADMIN |
| 관리자 | `GET /api/admin/posts`, `DELETE /api/admin/posts/{id}`, `POST /api/admin/notices` | ADMIN |
| 관리자 | `GET /api/admin/reports[/{id}]`, `PATCH /api/admin/reports/{id}` | ADMIN; 신고에 저장된 대상만 후속 조치 |
| 관리자 종목 | `GET /api/admin/sports`, `GET /api/admin/sports/proposals`, `POST /api/admin/sports/proposals/{id}/approve|reject|merge`, `POST /api/admin/sports/{id}/merge` | ADMIN |

미로그인은 401, 로그인한 일반 사용자의 관리자 접근은 403이다. SUSPENDED 사용자는 로그인,
기존 HTTP session, 새/기존 Socket.IO 연결 모두 제한된다. 만료된 기간 정지는 요청 시 ACTIVE로
자동 전환된다. role을 바꾸는 일반 API는 없다.

## 6. frontend 추가 화면

- 친구 검색·요청·목록·차단·개인톡 진입: `static/friends.html`
- 게시글 목록/검색과 상세/작성/댓글: `community.html`, `post-detail.html`
- 신고 접수/내 처리상태: `reports.html`
- 읽음/모두 읽음/읽지 않은 수: `notifications.html`
- 관심 모임: `favorites.html`
- 종목 신청: `sports.html`
- 회원·모임·신고·게시글·공지·종목 관리자: `static/admin/`
- 프로필 활동 통계와 모임 상세의 관심·신고·대기 순위는 기존 화면에 연결했다.

화면은 권한에 따라 버튼을 표시하지만 권한 판단은 전부 backend가 다시 수행한다. 사용자
문자열은 `escapeHtml` 또는 `textContent`로 출력한다.

## 7. 작성한 테스트

기존 31개를 포함한 전체 unittest를 실행한다.

```powershell
$env:TEST_MYSQL='1'
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

신규 테스트는 반대 방향 친구 요청 경쟁, 타인 요청 수락/차단 해제/게시글·댓글 변경/알림 읽음,
비멤버 채팅 조회·송신, 차단 후 송신, 일반 사용자 admin·신고 처리, report 대상 ID 주입,
정지 session/socket, 신고 제한 경쟁, 정원 초과 동시 참가, FIFO 승급·채팅 등록·알림,
교차 모임 동시 일정 충돌, 종목 중복 경쟁과 병합을 포함한다. `test_migrations.py`는 main 스키마에
001~010을 적용한 결과를 신규 `init.sql`과 컬럼·index·constraint 단위로 비교한다.

## 8. 아직 구현하지 않은 PRD 기능

이번 요청에 명시된 backend와 예시 frontend 범위는 구현했다. 요청에서 제외한 커뮤니티 이미지
업로드는 구현하지 않았다. 페이지 단위 pagination UI는 단순한 “더 보기” 방식이다. 모바일 push,
이메일 알림, 관리자 대량 작업은 이번 요구사항에 없으므로 포함하지 않았다.

## 9. 보안 검증 시 공격할 권한 경계

- URL의 request/comment/post/notification/report/chat_room/user ID를 다른 사용자 값으로 교체.
- body에 `user_id`, `reporter_id`, `processed_by`, `role`, `status`, `target_id`를 추가해 신원·처리
  대상을 바꾸려는 요청.
- 두 방향 친구 요청, DIRECT 생성, 신고, 즉시 참가를 동시에 반복해 UNIQUE/lock 우회.
- 차단 직전·직후 친구 수락과 메시지 송신 경쟁, 정지 직전 열린 Socket.IO에서 메시지 송신.
- 서로 겹치는 두 모임 동시 승인, 취소·강퇴·승급 동시 수행, max_participants 축소 경쟁.
- NOTICE를 FREE로 읽은 뒤 일반 사용자가 NOTICE로 변경, soft delete된 post/comment 재조작.
- `limit`, `offset`, 검색어, enum, bool-as-int, 과도한 Unicode/공백 입력.

## 10. EC2 배포 전 직접 확인

- DB snapshot/복구 절차와 위 두 preflight 결과.
- EC2 MySQL이 8.0이며 CHECK constraint와 generated column을 지원하는지.
- 애플리케이션과 migration이 모두 UTC를 사용하고 EC2/MySQL time zone이 예상과 맞는지.
- 기존 시작시간 23:30 이후 모임의 올바른 실제 종료시간.
- 실제 ADMIN 계정의 role을 DB 운영 절차로 부여했는지. role 변경 API는 없다.
- `SECRET_KEY`, DB 자격증명, `S3_BUCKET_NAME`, EC2 IAM role과 S3 presigned URL.
- Nginx의 Socket.IO upgrade 설정, 배포 후 열린 소켓 정지/차단 테스트.
- migration 성공 및 `--check`, app log, `/api/meetings`, 로그인, 이미지 URL, 기존 모임 채팅 smoke test.
- 모바일 너비에서 신규 화면과 긴 한국어/이모지 입력 표시.
