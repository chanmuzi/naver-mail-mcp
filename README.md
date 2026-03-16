# naver-mail-mcp

Naver Mail MCP Server for Claude Desktop.

네이버 메일을 Claude Desktop에서 사용할 수 있게 해주는 MCP(Model Context Protocol) 서버입니다.

## Features

- 메일 프로필 조회 (총 메일 수, 안읽은 메일 수)
- 메일 검색 (발신자, 수신자, 제목, 날짜, 읽음 여부)
- 메일 읽기 (본문, 첨부파일 정보)
- 메일 스레드 조회
- 폴더 목록 조회
- 초안 작성 및 목록 조회
- 메일 발송 (새 메일, 답장)
- 첨부파일 다운로드 (base64)

## Installation

```bash
uvx naver-mail-mcp
```

## Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "naver-email": {
      "command": "uvx",
      "args": ["naver-mail-mcp"],
      "env": {
        "NAVER_EMAIL_ADDRESS": "your_email@naver.com",
        "NAVER_EMAIL_PASSWORD": "your_app_password",
        "NAVER_FULL_NAME": "Your Name"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NAVER_EMAIL_ADDRESS` | Yes | Naver email address |
| `NAVER_EMAIL_PASSWORD` | Yes | Naver app password |
| `NAVER_FULL_NAME` | No | Display name for outgoing emails |

## Prerequisites

- Python 3.10+
- Naver account with IMAP/SMTP enabled
- Naver application password (2FA required)

## License

MIT
