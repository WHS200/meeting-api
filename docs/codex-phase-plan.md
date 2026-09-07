# Codex 확장 계획 / Phase 1

분석 기준: WHS200/meeting-api main `376101825cd6cdf7870ec41a7051bc341af898f4`.
2026-09-07 원격 refs/heads/main과 로컬 HEAD 일치 확인. 기존 requirements.txt 사용자 수정 보존.

## 현재 구조와 연결 지점

- server.py: Flask + Flask-SocketIO, 7개 기존 Blueprint, 단일 Gunicorn worker + threads 100.
- auth_gyumin: session user_id 인증, users.role/status 존재. 로그인은 DELETED만 제외해 SUSPENDED도 통과한다. login_required는 세션 존재만 검사한다.
- users/me는 user_id/role을 반환하지 않아 신규 화면에 필요한 두 필드를 읽기 응답에 추가한다. 일반 프로필 수정은 role을 쓰지 않는다.
- S3: shared.s3.generate_profile_image_url 재사용. profile.py가 실제 등록된 업로드 구현이며 profile_s3ver.py는 미등록 중복 구현이다.
- meetings_gyudong: CRUD, host/ADMIN 편집, meeting_date + meeting_time, end_time 없음. 모임 생성과 chat_rooms/host membership 생성은 한 트랜잭션.
- participation_euna: host를 제외한 APPROVED count + 1이 실제 정원. 신청/승인은 meetings FOR UPDATE 사용. 취소/강퇴/거절에는 잠금 추가 필요. 현재 참가 이력이 하나라도 있으면 재신청 불가.
- chat_dahyun: room_type 문자열, nullable meeting_id로 DIRECT 확장 가능. REST 조회/Socket.IO 송신 모두 chat_room_members 사용. 새 송신 제한은 Socket.IO에도 반드시 적용.
- DB: MySQL 8.0, users/sports/user_sports/meetings/meeting_participants/chat_rooms/chat_room_members/chat_messages 8개 테이블. 기존 001 migration 보존.
- frontend: 정적 HTML + vanilla JS, styles.css의 panel/btn/table 등, apiFetch의 same-origin cookie와 오류 처리, escapeHtml 재사용.
- tests: unittest와 cursor/connection fake 기반 5개 파일. 실제 DB 동시성 검증은 없음.
- Docker: 기존 named volume에는 init.sql 재적용 안 됨. migration은 app 업데이트 전에 실행해야 한다.
- README 및 모듈 README를 확인했고 별도 PRD 파일은 저장소에 없다. 이번 요구사항을 추가 명세로 사용한다.

## Phase별 산출물

| Phase | 구현 | migration |
|---|---|---|
| 2 | 친구/차단 + 권한/경쟁 요청 테스트 + 친구 화면 | 002_social |
| 3 | DIRECT 생성, 기존 조회/소켓 재사용, 차단 검사 | 003_direct_chat |
| 4 | 게시글/댓글/검색/NOTICE 권한, 커뮤니티 화면 | 004_community |
| 5 | 신고 대상 검증, 일/24시간 제한, 신고 화면 | 005_reports |
| 6 | 관리자/정지/운영 이력/신고 조치, 관리자 화면 | 006_admin |
| 7 | 알림과 기존 트랜잭션 연결 | 007_notifications |
| 8 | 관심 모임/SQL 활동 통계 | 008_favorites |
| 9 | WAITING/FIFO/승급, 시간/정원 잠금, 일정 입력 | 009_meeting_extensions |
| 10 | 종목 제안/승인/거절/병합 | 010_sports_management |

각 Phase는 구현 → migration/init 동기화 → 기능/권한 테스트 → 기존 전체 테스트 순서로 진행한다.
테스트 전용 MySQL을 사용해 신규 init과 기존 main+전체 migration의 최종 schema가 일치하는지 확인한다.

## 정책 결정

- 사용자 쌍은 작은 ID/큰 ID로 정규화한다. PENDING 요청은 generated nullable pair key UNIQUE로 양방향 중복 방어. 종료된 요청은 이력 보존.
- 정지 기간은 UTC DATETIME, 만료 후 자동 활성화. 일반 role 변경 API 없음. 관리자 조치 이력 보존.
- 신고 시각/일 제한은 UTC일 기준. 신고 대상 삭제 후에도 신고와 처리 이력을 보존한다.
- 같은 날짜의 시간 구간만 지원하며 30분~12시간. 신규 요청은 end_time 필요. 기존 데이터는 1시간, 자정 경계는 최대 23:59:59까지 보완 후 30분 미만 자료가 있으면 migration 전 수동 정정한다.
- 일정 충돌은 다른 모임의 APPROVED만 검사. 취소된 모임은 제외. 승인/승급 때에도 검사. 모임 수정으로 승인자의 충돌이 생겨도 거부한다.
- APPROVAL 모임의 만석 신청은 먼저 PENDING 심사를 거치며 host 승인 시 WAITING으로 배정한다. INSTANT 만석 신청은 바로 WAITING. 심사받지 않은 사용자를 자동 승인하지 않는다.
- WAITING 순서는 waiting_at과 user_id. 충돌/정지로 지금 승급할 수 없는 대기자는 유지하고 다음 승급 가능한 사람을 찾는다.
- 모임 행 잠금으로 정원을 보호하고 일정 변경용 DB mutex로 사용자별 교차 모임 승인/수정 경쟁을 직렬화한다. 작은 프로젝트에서 이해 가능한 정확성을 우선한다.
- 관리자 모임 조치는 상태 CANCELED로 보존한다. 게시글은 soft delete. 신고와 운영 기록을 유지한다.
- HTML은 사용자 값을 escapeHtml/textContent로 출력하며 권한은 서버에서 검사한다.
