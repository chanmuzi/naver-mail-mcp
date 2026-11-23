"""Offline security regressions. No real mail credentials or server required."""
import asyncio
import importlib
import contextlib
import io
import os
import runpy
import ssl
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from naver_mail_mcp import config, imap_client as imap, smtp_client as smtp, server


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
        with patch.object(imap.config, "max_message_bytes", return_value=10):
            with self.assertRaises(imap.MessageTooLargeError):
                imap.read_email(Mailbox(size=1, raw=b"x" * 11), "1")

    def test_message_limit_is_configurable(self):
        two_mib = 2 * 1024 * 1024
        with patch.dict("os.environ", {"NAVER_MAIL_MAX_MESSAGE_MB": "1"}):
            with self.assertRaises(imap.MessageTooLargeError) as error:
                imap.read_email(Mailbox(size=two_mib), "1")
            self.assertIn("NAVER_MAIL_MAX_MESSAGE_MB", str(error.exception))
        with patch.dict("os.environ", {"NAVER_MAIL_MAX_MESSAGE_MB": "3"}):
            self.assertEqual(imap.read_email(Mailbox(size=two_mib), "1").subject, "hello")

    def test_default_message_limit_and_invalid_values(self):
        with patch.dict("os.environ", {"NAVER_MAIL_MAX_MESSAGE_MB": ""}):
            self.assertEqual(config.max_message_bytes(), 50 * 1024 * 1024)
        for value in ("0", "-1", "abc", "1.5", "１０"):
            with self.subTest(value=value), patch.dict("os.environ", {"NAVER_MAIL_MAX_MESSAGE_MB": value}):
                with self.assertRaises(ValueError):
                    config.max_message_bytes()

    def test_missing_uid_reports_not_found(self):
        box = Mailbox()
        box.uid = MagicMock(return_value=("OK", [None]))
        with self.assertRaises(imap.EmailNotFoundError):
            imap.read_email(box, "999")
        self.assertEqual(box.uid.call_count, 1)

    def test_thread_keeps_headers_of_oversized_message(self):
        small = b"Subject: small\r\nMessage-ID: <a@example.test>\r\n\r\nbody"
        large_headers = b"Subject: large\r\nMessage-ID: <b@example.test>\r\n\r\n"
        sizes = {"1": 100, "2": 100 * 1024 * 1024}
        fetched = []

        class ThreadBox(Mailbox):
            def uid(self, command, *args):
                if command == "SEARCH":
                    return "OK", [b"1 2"]
                uid = args[0].decode() if isinstance(args[0], bytes) else args[0]
                fetched.append((uid, args[-1]))
                if args[-1] == "(RFC822.SIZE)":
                    return "OK", [f"{uid} (UID {uid} RFC822.SIZE {sizes[uid]})".encode()]
                if "BODY.PEEK[HEADER]<0." in args[-1]:
                    return "OK", [(b"2 (UID 2 FLAGS (\\Seen)", large_headers), b")"]
                return "OK", [(f"{uid} (UID {uid} FLAGS ()".encode(), small), b")"]

        thread = imap.read_thread(ThreadBox(), "<a@example.test>")
        by_subject = {mail.subject: mail for mail in thread}
        self.assertEqual(set(by_subject), {"small", "large"})
        self.assertEqual(by_subject["small"].notice, "")
        self.assertEqual(by_subject["small"].body_text, "body")
        self.assertIn("exceeds", by_subject["large"].notice)
        self.assertEqual(by_subject["large"].body_text, "")
        self.assertEqual(by_subject["large"].flags, ["\\Seen"])
        # The oversized body itself must never be requested.
        self.assertFalse(any(uid == "2" and "BODY.PEEK[]" in item for uid, item in fetched))

    def test_write_tools_enabled_by_default_and_hidden_when_read_only(self):
        try:
            for value, read_only in (("", False), ("0", False), ("false", False), ("1", True), ("true", True), ("ture", True)):
                with self.subTest(value=value), patch.dict("os.environ", {"NAVER_MAIL_READ_ONLY": value}):
                    importlib.reload(server)
                    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
                    self.assertEqual(len(names), 7 if read_only else 9)
                    self.assertEqual("send_email" in names, not read_only)
                    self.assertEqual("create_draft" in names, not read_only)
            with patch.dict("os.environ", {"NAVER_MAIL_READ_ONLY": "1"}):
                for call in (
                    lambda: server.send_email(["to@example.test"], "hi", "body"),
                    lambda: server.create_draft(["to@example.test"], "hi", "body"),
                ):
                    with self.assertRaises(PermissionError):
                        call()
        finally:
            importlib.reload(server)

    def test_read_only_unset_keeps_write_tools(self):
        env = {k: v for k, v in os.environ.items() if k != "NAVER_MAIL_READ_ONLY"}
        with patch.dict("os.environ", env, clear=True):
            self.assertFalse(config.is_read_only())

    def test_message_id_rejects_unsafe_quoted_string_characters(self):
        for mid in ("<a\x00b>", "<a\\>", "<결제>", '<a"b>', "<a b>", "<a><b>", "<>", "", ".", "@", "a@b", "<" + "a" * 998 + ">"):
            with self.subTest(mid=mid), self.assertRaises(ValueError):
                imap._sanitize_message_id(mid)
        for mid in ("<a@example.test>", "<CA+x_y=z.1$2%3@mail.example.test>", "<local-only>", "<a[1]@example.test>"):
            with self.subTest(mid=mid):
                self.assertEqual(imap._sanitize_message_id(mid), mid)

    def test_thread_lookup_adds_missing_brackets(self):
        box = Mailbox(raw=b"Subject: hello\r\nMessage-ID: <a@example.test>\r\n\r\nbody")
        imap.read_thread(box, " a@example.test ")
        first_search = [call for call in box.calls if call[0] == "SEARCH"][0]
        self.assertEqual(first_search[1][-1], 'HEADER Message-ID "<a@example.test>"')

    def test_thread_ignores_substring_ids_from_headers(self):
        headers = b"References: . @ <real@example.test>\r\n\r\n"
        searched = []

        class Box(Mailbox):
            def uid(self, command, *args):
                if command == "SEARCH":
                    searched.append(args[-1])
                    return "OK", [b"1"]
                if "HEADER.FIELDS" in args[-1]:
                    return "OK", [(b"1 (UID 1", headers), b")"]
                return super().uid(command, *args)

        imap.read_thread(Box(), "<a@example.test>")
        self.assertTrue(any('"<real@example.test>"' in item for item in searched))
        self.assertFalse(any(item.endswith(('"."', '"@"')) for item in searched))

    def test_thread_caps_ids_and_messages(self):
        many_refs = " ".join(f"<r{i}@example.test>" for i in range(500)).encode()
        searched = []

        class Box(Mailbox):
            result = b"1"

            def uid(self, command, *args):
                if command == "SEARCH":
                    searched.append(args[-1])
                    return "OK", [self.result]
                if "HEADER.FIELDS" in args[-1]:
                    return "OK", [(b"1 (UID 1", b"References: " + many_refs + b"\r\n\r\n"), b")"]
                return super().uid(command, *args)

        imap.read_thread(Box(), "<a@example.test>")
        self.assertEqual(len(searched), 1 + 3 * imap.MAX_THREAD_IDS)

        flood = Box()
        flood.result = b" ".join(str(i).encode() for i in range(1, 502))
        with self.assertRaises(imap.NaverIMAPError) as error:
            imap.read_thread(flood, "<a@example.test>")
        self.assertIn("exceeds the limit", str(error.exception))
        self.assertFalse(any(call[1][-1] == "(RFC822.SIZE)" for call in flood.calls))

    def test_malformed_date_does_not_break_reads(self):
        raw = b"Subject: odd\r\nDate: Mon, 32 Foo 2026 99:99:99\r\n\r\nbody"
        mail = imap.read_email(Mailbox(raw=raw), "1")
        self.assertEqual((mail.subject, mail.date, mail.body_text), ("odd", "", "body"))
        self.assertEqual(imap.search_emails(Mailbox(raw=raw)).emails[0].date, "")

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
