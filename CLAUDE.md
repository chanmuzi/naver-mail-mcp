# CLAUDE.md

## Project Overview

네이버 메일 전용 MCP 서버 (Python, FastMCP).
기존 mcp-email-server가 네이버 IMAP과 호환되지 않아 커스텀 구현.

## Tools (9개)

`get_profile`, `search_emails`, `read_email`, `read_thread`, `list_folders`, `create_draft`, `list_drafts`, `send_email`, `download_attachment`

`NAVER_MAIL_READ_ONLY=1`이면 쓰기 도구인 `create_draft`, `send_email`은 등록되지 않는다 (7개).

## Security

보안 리뷰 완료 — 아래 패턴이 적용되어 있으며 반드시 유지할 것:
- TLS 인증서와 호스트명 검증 (`ssl.create_default_context()`)
- IMAP injection 방지 (검색 값은 quoted string 또는 UTF-8 literal로 전송, 제어 문자 거부)
- Header injection 방지
- DoS 방지 (메일 크기 사전 확인 `NAVER_MAIL_MAX_MESSAGE_MB`, 첨부파일 크기 제한 등)

## Testing

- 오프라인 보안 회귀 테스트: `python -m unittest discover -s tests -p 'test_security.py'` (계정 불필요)
- 자동화된 통합 테스트: `python -m tests.test_integration` (실제 네이버 IMAP/SMTP 서버 대상, `send_email` 제외, 실패 시 exit code 1)
- `send_email`은 실제 메일이 발송되므로 자동화된 통합 테스트에서 제외하며, 별도 수동 테스트가 필요
