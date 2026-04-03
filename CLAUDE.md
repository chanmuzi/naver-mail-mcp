# CLAUDE.md

## Project Overview

네이버 메일 전용 MCP 서버 (Python, FastMCP).
기존 mcp-email-server가 네이버 IMAP과 호환되지 않아 커스텀 구현.

## Tools (9개)

`get_profile`, `search_emails`, `read_email`, `read_thread`, `list_folders`, `create_draft`, `list_drafts`, `send_email`, `download_attachment`

## Security

보안 리뷰 완료 — 아래 패턴이 적용되어 있으며 반드시 유지할 것:
- IMAP injection 방지
- Header injection 방지
- DoS 방지 (첨부파일 크기 제한 등)

## Testing

- 자동화된 통합 테스트: 8/8 PASS (실제 네이버 IMAP/SMTP 서버 대상, `send_email` 제외)
- `send_email`은 실제 메일이 발송되므로 자동화된 통합 테스트에서 제외하며, 별도 수동 테스트가 필요
