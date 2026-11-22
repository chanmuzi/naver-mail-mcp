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

## Security defaults

- IMAP/SMTP connections verify the server certificate and hostname using the system trust store.
- Search values are quoted or sent as UTF-8 literals, and control characters are rejected. Every filter is kept: if the server rejects a search, the call fails instead of silently searching with fewer filters.
- `create_draft` and `send_email` are enabled by default. Set `NAVER_MAIL_READ_ONLY=1` **before starting the server** to remove them from the tool list, then restart the client.
- Body and attachment downloads reject messages larger than **50 MiB including MIME encoding and headers**. The server checks `RFC822.SIZE` before requesting a bounded `BODY.PEEK` response. Change the limit with `NAVER_MAIL_MAX_MESSAGE_MB`. In `read_thread`, an oversized message is returned with headers only and a `notice` explaining why the body is missing.
- A single attachment larger than 10 MiB (decoded) is not returned by `download_attachment`.
- `read_thread` accepts only whole Message-IDs in the form `<id@domain>` and stops if a thread matches more than 50 messages, so a crafted `References` header cannot pull in the whole folder.
- Read-only mode is a tool policy, not a credential scope: the app password keeps its full server-side permissions. Keep credentials outside version control, and treat mail content as untrusted data, not as instructions to invoke tools.

Offline security regression tests (no mail account needed):

```bash
uv run python -m unittest discover -s tests -p 'test_security.py' -v
```

## Installation

```bash
uvx naver-mail-mcp
```

## Claude Desktop Configuration

### PyPI 배포 후 (권장)

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

### 로컬 개발 모드

PyPI에 배포하기 전, 로컬 소스에서 직접 실행:

```json
{
  "mcpServers": {
    "naver-email": {
      "command": "/absolute/path/to/uv",
      "args": [
        "--directory",
        "/absolute/path/to/naver-mail-mcp",
        "run",
        "naver-mail-mcp"
      ],
      "env": {
        "NAVER_EMAIL_ADDRESS": "your_email@naver.com",
        "NAVER_EMAIL_PASSWORD": "your_app_password",
        "NAVER_FULL_NAME": "Your Name"
      }
    }
  }
}
```

> **주의:** Claude Desktop은 시스템 PATH를 상속하지 않습니다. `command`에는 반드시 `uv`의 **절대 경로**를 사용하세요. (예: `/Users/username/.local/bin/uv`)
>
> `which uv` 명령으로 절대 경로를 확인할 수 있습니다.

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
| `NAVER_MAIL_READ_ONLY` | No | `1`이면 `create_draft`, `send_email` 도구를 등록하지 않음 (기본: 비활성화, 9개 도구 모두 사용) |
| `NAVER_MAIL_MAX_MESSAGE_MB` | No | 내려받을 메일의 최대 크기 (MiB, 헤더와 MIME 인코딩 포함, 기본 50) |

## Tools Reference

### get_profile
계정 프로필 조회. 파라미터 없음.

### search_emails
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| folder | string | No | INBOX | 검색할 폴더 |
| sender | string | No | - | 발신자 필터 |
| recipient | string | No | - | 수신자 필터 |
| subject | string | No | - | 제목 키워드 |
| date_from | string | No | - | 시작 날짜 (DD-Mon-YYYY) |
| date_to | string | No | - | 종료 날짜 (DD-Mon-YYYY) |
| is_read | boolean | No | - | 읽음 여부 (true/false/null) |
| page | integer | No | 1 | 페이지 번호 |
| page_size | integer | No | 20 | 페이지당 결과 수 (최대 100) |

### read_email
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| uid | string | Yes | - | 메일 고유 ID |
| folder | string | No | INBOX | 폴더 |

### read_thread
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| message_id | string | Yes | - | Message-ID 헤더 값 |
| folder | string | No | INBOX | 폴더 |

### list_folders
폴더 목록 조회. 파라미터 없음.

### create_draft
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| to | array | Yes | - | 수신자 목록 |
| subject | string | Yes | - | 제목 |
| body | string | Yes | - | 본문 |
| body_type | string | No | text/plain | text/plain 또는 text/html |
| cc | array | No | - | 참조 목록 |

### list_drafts
초안 목록 조회. 파라미터 없음.

### send_email
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| to | array | Yes | - | 수신자 목록 |
| subject | string | Yes | - | 제목 |
| body | string | Yes | - | 본문 |
| body_type | string | No | text/plain | text/plain 또는 text/html |
| cc | array | No | - | 참조 목록 |
| in_reply_to | string | No | - | 답장 대상 Message-ID |
| references | array | No | - | 스레드 Message-ID 목록 |

### download_attachment
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| uid | string | Yes | - | 메일 고유 ID |
| part_number | string | Yes | - | MIME 파트 번호 (read_email에서 확인) |
| folder | string | No | INBOX | 폴더 |

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

# Run offline security tests (no account needed)
python -m unittest discover -s tests -p 'test_security.py' -v

# Run integration tests (real Naver account, read-only)
python -m tests.test_integration
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `IMAP authentication failed` | 앱 비밀번호 확인. 계정 비밀번호가 아닌 애플리케이션 비밀번호 사용 |
| `Cannot connect to Naver IMAP server` | 네트워크 확인, IMAP 사용 설정 확인 |
| `Missing required environment variables` | NAVER_EMAIL_ADDRESS, NAVER_EMAIL_PASSWORD 환경변수 설정 |
| `Folder not found` | `list_folders` 도구로 사용 가능한 폴더명 확인 |
| `Message ... exceeds the ...-byte limit` | `NAVER_MAIL_MAX_MESSAGE_MB` 값을 높인 뒤 서버 재시작 |
| `create_draft`, `send_email` 도구가 보이지 않음 | `NAVER_MAIL_READ_ONLY` 설정 여부 확인 |
| `Failed to spawn process` | `command`에 `uv`의 절대 경로 사용 (`which uv`로 확인) |

## Technical Details

- **IMAP**: `imap.naver.com:993` (SSL/TLS)
- **SMTP**: `smtp.naver.com:465` (SSL)
- **Transport**: stdio (Claude Desktop 연동)
- **Encoding**: UTF-8, EUC-KR, Modified UTF-7 (폴더명) 자동 처리
- **Connection**: 각 도구 호출마다 새 연결 (stateless)
- **Attachment limit**: 10MiB (디코딩 후 첨부파일 1개 기준)
- **Message limit**: 50MiB (`NAVER_MAIL_MAX_MESSAGE_MB`로 조정)

## License

MIT
