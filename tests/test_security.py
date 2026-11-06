"""Offline security regressions. No real mail credentials or server required."""
import asyncio
import importlib
import contextlib
import io
import runpy
import ssl
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from naver_mail_mcp import imap_client as imap, smtp_client as smtp, server


class Mailbox:
    def __init__(self, size=100, raw=b"Subject: hello\r\n\r\nbody"):
        self.size, self.raw = size, raw
        self.calls = []
        self.literal = None

    def select(self, *args, **kwargs):
        return "OK", [b"1"]

    def uid(self, command, *args):
        self.calls.append((command, args, self.literal))
        if command == "SEARCH":
            return "OK", [b"1"]
        if args[-1] == "(RFC822.SIZE)":
            return "OK", [f"1 (UID 1 RFC822.SIZE {self.size})".encode()]
        return "OK", [(b"1 (UID 1 FLAGS ())", self.raw), b")"]


class SecurityTests(unittest.TestCase):
    def test_imap_checks_server_identity(self):
        with patch.object(imap.imaplib, "IMAP4_SSL") as connect:
            with imap.imap_connection("dummy@example.test", "dummy"):
                pass
        context = connect.call_args.kwargs.get("ssl_context")
        self.assertIsNotNone(context)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_smtp_checks_server_identity(self):
        with patch.object(smtp.smtplib, "SMTP_SSL") as connect:
            smtp.send_email("dummy@example.test", "dummy", "", ["to@example.test"], "hi", "body")
        context = connect.call_args.kwargs.get("context")
        self.assertIsNotNone(context)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_search_rejects_control_characters(self):
        for field in ("sender", "recipient", "subject", "date_from", "date_to"):
            for value in ("x\r\nZ999 LOGOUT", "x\x00y"):
                with self.subTest(field=field, value=value):
                    box = Mailbox()
                    with self.assertRaises(ValueError):
                        imap.search_emails(box, **{field: value})
                    self.assertEqual(box.calls, [])

    def test_ascii_search_quotes_special_characters(self):
        box = Mailbox()
        imap.search_emails(box, subject='a "quoted" \\ value')
        args = box.calls[0][1]
        self.assertIn('"a \\"quoted\\" \\\\ value"', args)

    def test_unicode_search_uses_literal_without_dropping_filters(self):
        box = Mailbox()
        imap.search_emails(box, sender="sender@example.test", subject="결제")
        searches = [call for call in box.calls if call[0] == "SEARCH"]
        self.assertTrue(any('"sender@example.test"' in call[1] for call in searches))
        self.assertTrue(any(call[2] == "결제".encode() for call in searches))
        self.assertIsNone(box.literal)

    def test_search_error_does_not_retry_with_weaker_filters(self):
        box = Mailbox()
        box.uid = MagicMock(side_effect=imap.imaplib.IMAP4.error("unsupported"))
        with self.assertRaises(imap.imaplib.IMAP4.error):
            imap.search_emails(box, subject="결제")
        self.assertEqual(box.uid.call_count, 1)

    def test_multiple_unicode_filters_intersect_uids(self):
        box = Mailbox()
        original = box.uid

        def uid(command, *args):
            if command == "SEARCH":
                return "OK", [b"1 2" if box.literal == "결제".encode() else b"2 3"]
            return original(command, *args)

        box.uid = uid
        result = imap.search_emails(box, subject="결제", sender="네이버")
        self.assertEqual([mail.uid for mail in result.emails], ["2"])

    def test_large_message_rejected_before_body_fetch(self):
        for reader in (lambda b: imap.read_email(b, "1"), lambda b: imap.download_attachment(b, "1", "1")):
            box = Mailbox(size=100 * 1024 * 1024)
            with self.assertRaises(imap.NaverIMAPError):
                reader(box)
            self.assertEqual([call[1][-1] for call in box.calls], ["(RFC822.SIZE)"])

    def test_unknown_size_fails_closed(self):
        box = Mailbox()
        box.uid = MagicMock(return_value=("OK", [b"1 (UID 1)"]))
        with self.assertRaises(imap.NaverIMAPError):
            imap.read_email(box, "1")
        self.assertEqual(box.uid.call_count, 1)

    def test_body_fetch_is_peek_and_bounded(self):
        box = Mailbox()
        mail = imap.read_email(box, "1")
        self.assertEqual(mail.subject, "hello")
        self.assertIn("BODY.PEEK[]<0.", box.calls[-1][1][-1])

    def test_response_exceeding_limit_rejected(self):
        with patch.object(imap, "MAX_MESSAGE_BYTES", 10, create=True):
            with self.assertRaises(imap.NaverIMAPError):
                imap.read_email(Mailbox(size=1, raw=b"x" * 11), "1")

    def test_write_tools_require_opt_in(self):
        try:
            for enabled in ("", "1"):
                with patch.dict("os.environ", {"NAVER_MAIL_ENABLE_WRITES": enabled}):
                    importlib.reload(server)
                    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
                    self.assertEqual("send_email" in names, enabled == "1")
                    self.assertEqual("create_draft" in names, enabled == "1")
            with patch.dict("os.environ", {"NAVER_MAIL_ENABLE_WRITES": ""}):
                with self.assertRaises(PermissionError):
                    server.send_email(["to@example.test"], "hi", "body")
        finally:
            importlib.reload(server)

    def test_message_id_rejects_unsafe_quoted_string_characters(self):
        for mid in ("<a\x00b>", "<a\\>", "<결제>"):
            with self.subTest(mid=mid), self.assertRaises(ValueError):
                imap._sanitize_message_id(mid)

    def test_integration_runner_exits_nonzero_on_failure(self):
        path = Path(__file__).with_name("test_integration.py")
        with patch.dict("os.environ", {"NAVER_EMAIL_ADDRESS": "dummy@example.test", "NAVER_EMAIL_PASSWORD": "dummy"}):
            with patch.object(Path, "exists", return_value=False), patch.object(imap, "imap_connection", side_effect=OSError("offline")):
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
                    runpy.run_path(str(path), run_name="__main__")
        self.assertEqual(error.exception.code, 1)

    def test_literal_is_serialized_by_real_imaplib(self):
        wire = object.__new__(imap.imaplib.IMAP4)
        wire.state, wire._encoding = "SELECTED", "ascii"
        wire.untagged_responses = {}
        wire.is_readonly, wire.utf8_enabled, wire.debug = True, False, 0
        wire._new_tag = lambda: b"A001"
        wire._log = lambda *args: None
        wire._get_response = lambda: None
        sent = []
        wire.send = sent.append
        box = Mailbox()
        original = box.uid

        def uid(command, *args):
            if command == "SEARCH":
                wire.literal = box.literal
                wire._command("UID", command, *args)
            return original(command, *args)

        box.uid = uid
        imap.search_emails(box, subject="결제")
        self.assertEqual(sent, [b"A001 UID SEARCH CHARSET UTF-8 SUBJECT {6}\r\n", "결제".encode(), b"\r\n"])


if __name__ == "__main__":
    unittest.main()
