# Test Results — Naver Mail MCP Server

## Environment
- Date: 2026-03-16
- Python: 3.12.12
- MCP SDK: 1.26.0
- OS: macOS (Darwin 25.3.0)

## Unit Tests (Encoding Utilities)

| Test | Status | Notes |
|------|--------|-------|
| mUTF-7 encode ASCII | PASS | INBOX, Sent Messages, Drafts roundtrip |
| mUTF-7 encode Korean | PASS | 받은메일함 roundtrip |
| mUTF-7 ampersand | PASS | & → &- → & |
| RFC 2047 UTF-8 header | PASS | =?UTF-8?B?...?= → 한글 메일 테스트 |
| EUC-KR decode | PASS | charset 명시 시 정상 |
| Charset fallback chain | PASS | charset 없이도 한글 디코딩 |

## Security Tests

| Test | Status | Notes |
|------|--------|-------|
| Folder name injection | PASS | `"` 포함 시 ValueError |
| Message-ID injection | PASS | `"` 포함 시 ValueError |
| UID validation | PASS | 비숫자 거부 |
| Header CRLF injection | PASS | `\r\n` 포함 시 ValueError |
| body_type whitelist | PASS | text/plain, text/html만 허용 |
| Pagination bounds | PASS | page<1, page_size>100 거부 |
| Missing env vars | PASS | 명확한 에러 메시지 |
| Wrong password | PASS | AuthenticationError 정상 발생 |

## Integration Tests (Real Naver Server)

| Tool | Status | Notes |
|------|--------|-------|
| get_profile | PASS | total: 5000, unseen: 0 정상 반환 |
| list_folders | PASS | 10개 폴더 — INBOX, Sent Messages, Drafts, Deleted Messages, Junk, 내게쓴메일함, 깃허브, papers, 결제, 보안 |
| search_emails | PASS | 5000건 중 page=1, page_size=5 반환, 한글 제목 정상 |
| read_email | PASS | UID 13979, 한글 제목, HTML 본문 4673자 |
| read_thread | PASS | Message-ID 기반 스레드 조회 (1건 스레드) |
| create_draft | - | 수동 테스트 필요 |
| list_drafts | PASS | 4개 초안 정상 조회, 한글 제목 포함 |
| send_email | - | 수동 테스트 필요 (실제 발송 방지) |
| download_attachment | PASS | PNG 303,778 bytes → base64 405,040자 정상 |

## Korean Encoding Tests

| Scenario | Status | Notes |
|----------|--------|-------|
| Korean subject display | PASS | [카카오뮤직] D-7 탈퇴 예정 안내 |
| Korean body (UTF-8) | PASS | HTML 본문 한글 정상 |
| Korean folder names | PASS | 내게쓴메일함, 깃허브, 결제, 보안 — mUTF-7 디코딩 정상 |
| Korean search term | - | 추후 테스트 필요 |

## Error Handling Tests

| Scenario | Status | Notes |
|----------|--------|-------|
| Wrong password | PASS | "IMAP authentication failed. Check your Naver email address and app password." |
| Missing env vars | PASS | "Missing required environment variables: ..." |
| Nonexistent UID | - | 추후 테스트 필요 |
| Invalid folder name | - | 추후 테스트 필요 |

## Naver IMAP 특이사항

- 폴더명은 영문으로 반환됨 (INBOX, Sent Messages, Drafts, Deleted Messages, Junk)
- 사용자 생성 폴더는 mUTF-7로 인코딩 (내게쓴메일함 → &sLSsjMT0ulTHfNVo-)
- SEARCH ALL 정상 동작 확인
- UID FETCH (FLAGS RFC822) 정상 동작 확인
- Drafts 폴더명은 "Drafts" (영문)
- Sent 폴더명은 "Sent Messages"

## Issues Found

(none)

## Changelog

| Date | Changes |
|------|---------|
| 2026-03-16 | 초기 테스트: 인코딩 유닛 6개, 보안 8개, 통합 7개 PASS |
