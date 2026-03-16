# naver-mail-mcp

Naver Mail MCP Server for Claude Desktop.

네이버 메일을 Claude Desktop에서 Gmail MCP처럼 사용할 수 있게 해주는 MCP(Model Context Protocol) 서버입니다.

## Features

| Tool | Description |
|------|-------------|
| `get_profile` | 계정 프로필 조회 (이메일, 이름, 총 메일 수, 안읽은 수) |
| `search_emails` | 메일 검색 (발신자, 수신자, 제목, 날짜, 읽음 여부) + 페이지네이션 |
| `read_email` | UID로 메일 전체 읽기 (헤더, 본문, 첨부파일 메타정보) |
| `read_thread` | Message-ID 기반 대화 스레드 조회 |
| `list_folders` | 메일함 폴더 목록 조회 (메시지 수, 안읽은 수 포함) |
| `create_draft` | 새 메일 초안을 Drafts 폴더에 저장 |
| `list_drafts` | Drafts 폴더의 초안 목록 조회 |
| `send_email` | SMTP로 메일 발송 (새 메일, 답장) |
| `download_attachment` | 첨부파일 다운로드 (base64 인코딩) |

## Installation

```bash
uvx naver-mail-mcp
```

## Claude Desktop Configuration

`claude_desktop_config.json`에 추가:

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

## Prerequisites

1. **Python 3.10+**
2. **네이버 계정**에서 IMAP/SMTP 사용 설정
   - 네이버 메일 → 설정 → POP3/IMAP 설정 → IMAP/SMTP 사용 ✅
3. **애플리케이션 비밀번호** 발급 (2단계 인증 필수)
   - 네이버 → 내 정보 → 보안설정 → 2단계 인증 → 애플리케이션 비밀번호 관리

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NAVER_EMAIL_ADDRESS` | Yes | 네이버 이메일 주소 |
| `NAVER_EMAIL_PASSWORD` | Yes | 애플리케이션 비밀번호 (계정 비밀번호 아님) |
| `NAVER_FULL_NAME` | No | 발신 메일 표시 이름 |

## Development

```bash
# Clone and install
git clone https://github.com/chanmuzi/naver-mail-mcp.git
cd naver-mail-mcp
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e .

# Set credentials
cp .env.example .env
# Edit .env with your credentials

# Run tests
python -m tests.test_integration
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `IMAP authentication failed` | 앱 비밀번호 확인. 계정 비밀번호가 아닌 애플리케이션 비밀번호 사용 |
| `Cannot connect to Naver IMAP server` | 네트워크 확인, IMAP 사용 설정 확인 |
| `Missing required environment variables` | NAVER_EMAIL_ADDRESS, NAVER_EMAIL_PASSWORD 환경변수 설정 |
| `Folder not found` | `list_folders` 도구로 사용 가능한 폴더명 확인 |

## Technical Details

- **IMAP**: `imap.naver.com:993` (SSL/TLS)
- **SMTP**: `smtp.naver.com:465` (SSL)
- **Transport**: stdio (Claude Desktop 연동)
- **Encoding**: UTF-8, EUC-KR, Modified UTF-7 (폴더명) 자동 처리
- **Connection**: 각 도구 호출마다 새 연결 (stateless)
- **Attachment limit**: 10MB (base64 인코딩)

## License

MIT
