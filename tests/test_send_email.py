import json
import smtplib
import socket

import pytest

from conftest import write_shell_json

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"
PASSWORD = "abcd efgh ijkl mnop"


def run(ks, capsys, *argv):
    code = ks.main(list(argv))
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    return code, lines


@pytest.fixture
def book(tmp_path):
    path = tmp_path / "Dune.epub"
    path.write_bytes(b"PK\x03\x04 tiny epub")
    return path


@pytest.fixture
def setup_done(home, keyring):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER)
    keyring.set_password(PASSWORD + "\n")


def test_sending_a_small_epub_prints_sending_then_sent(ks, smtp, setup_done, book, capsys):
    code, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert code == 0
    assert lines == [{"stage": "sending"}, {"result": "sent"}]
    [server] = smtp.instances
    assert (server.host, server.port) == ("smtp.gmail.com", 465)
    assert server.logins == [(SENDER, PASSWORD)]
    assert len(server.sent) == 1


@pytest.mark.parametrize(
    "name, mime",
    [
        ("Dune.epub", "application/epub+zip"),
        ("Paper.PDF", "application/pdf"),
        ("notes.txt", "text/plain"),
        ("Essay.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("cover.jpg", "image/jpeg"),
    ],
)
def test_message_has_one_attachment_with_the_format_mime_type(ks, tmp_path, name, mime):
    book = tmp_path / name
    book.write_bytes(b"content")

    msg = ks.build_message(book, SENDER, KINDLE)

    assert msg["From"] == SENDER
    assert msg["To"] == KINDLE
    [attachment] = list(msg.iter_attachments())
    assert attachment.get_content_type() == mime
    assert attachment.get_filename() == name
    assert attachment.get_payload(decode=True) == b"content"


def test_subject_is_file_name_without_extension(ks, tmp_path):
    book = tmp_path / "The Left Hand of Darkness.epub"
    book.write_bytes(b"x")

    assert ks.build_message(book, SENDER, KINDLE)["Subject"] == "The Left Hand of Darkness"


@pytest.mark.parametrize(
    "settings, missing",
    [
        ({"senderAddress": SENDER}, "kindleAddress"),
        ({"kindleAddress": KINDLE}, "senderAddress"),
        ({"kindleAddress": KINDLE, "senderAddress": ""}, "senderAddress"),
    ],
)
def test_missing_setting_fails_before_connecting(
    ks, smtp, home, keyring, book, capsys, settings, missing
):
    write_shell_json(home, **settings)
    keyring.set_password(PASSWORD)

    code, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert code == 0
    assert lines == [
        {"result": "failed", "reason": f"Not set up: {missing} missing.", "fixBySetup": True,
         "field": missing}
    ]
    assert smtp.instances == []


def test_no_shell_json_names_both_settings(ks, smtp, home, keyring, book, capsys):
    keyring.set_password(PASSWORD)

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines == [
        {
            "result": "failed",
            "reason": "Not set up: kindleAddress, senderAddress missing.",
            "fixBySetup": True,
            "field": "kindleAddress",
        }
    ]
    assert smtp.instances == []


@pytest.mark.parametrize("stored", [None, "", "\n"])
def test_missing_or_empty_password_fails_before_connecting(
    ks, smtp, home, keyring, book, capsys, stored
):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER)
    if stored is not None:
        keyring.set_password(stored)

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines == [{"result": "failed", "reason": "No app password stored.", "fixBySetup": True,
                      "field": "appPassword"}]
    assert smtp.instances == []
    assert keyring.calls() == ["lookup service kindle-send user sender@gmail.com"]


def test_settings_path_can_be_overridden(ks, smtp, home, keyring, book, capsys, tmp_path, monkeypatch):
    other = tmp_path / "elsewhere.json"
    other.write_text(json.dumps({"plugins": [
        {"id": "sorydi3.kindle-send", "kindleAddress": KINDLE, "senderAddress": SENDER}]}))
    monkeypatch.setenv("KINDLE_SEND_SHELL_JSON", str(other))
    keyring.set_password(PASSWORD)

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines[-1] == {"result": "sent"}


def test_rejected_password_asks_for_setup(ks, smtp, setup_done, book, capsys):
    smtp.login_error = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines == [
        {"stage": "sending"},
        {"result": "failed", "reason": "Gmail rejected the app password.", "fixBySetup": True,
         "field": "appPassword"},
    ]


@pytest.mark.parametrize(
    "where, error, shown",
    [
        ("connect", socket.gaierror(-3, "Temporary failure in name resolution"),
         "[Errno -3] Temporary failure in name resolution"),
        ("connect", TimeoutError("timed out"), "timed out"),
        ("send", smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
         "Connection unexpectedly closed"),
    ],
)
def test_network_or_smtp_error_names_the_error(ks, smtp, setup_done, book, capsys, where, error, shown):
    setattr(smtp, f"{where}_error", error)

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines[-1] == {"result": "failed", "reason": f"Couldn't reach Gmail: {shown}."}


def test_book_bigger_than_advertised_size_is_not_sent(ks, smtp, setup_done, tmp_path, capsys):
    big = tmp_path / "Atlas.pdf"
    big.write_bytes(b"x" * 3_000_000)
    smtp.advertised_size = 1_000_000

    _, lines = run(ks, capsys, "send", "--route", "email", str(big))

    assert lines[-1] == {"result": "failed", "reason": "Too big for email (3 MB). Switch it to USB."}
    assert smtp.instances[0].sent == []


def test_server_refusing_size_is_too_big(ks, smtp, setup_done, tmp_path, capsys):
    big = tmp_path / "Atlas.pdf"
    big.write_bytes(b"x" * 2_000_000)
    smtp.send_error = smtplib.SMTPSenderRefused(552, b"5.3.4 Message size exceeds fixed limit", SENDER)

    _, lines = run(ks, capsys, "send", "--route", "email", str(big))

    assert lines[-1] == {"result": "failed", "reason": "Too big for email (2 MB). Switch it to USB."}


def test_advertised_size_is_cached_for_plan(ks, smtp, setup_done, book, home, capsys):
    smtp.advertised_size = 12_345_678

    run(ks, capsys, "send", "--route", "email", str(book))

    cache = home / ".local" / "state" / "kindle-send" / "email-limit.json"
    assert json.loads(cache.read_text()) == {"advertised": 12_345_678}


def test_format_email_cannot_carry_fails_without_connecting(ks, smtp, setup_done, tmp_path, capsys):
    book = tmp_path / "Dune.azw3"
    book.write_bytes(b"x")

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines == [{"result": "failed", "reason": "AZW3 can't be sent by email. Switch it to USB."}]
    assert smtp.instances == []


def history(home):
    path = home / ".local" / "state" / "kindle-send" / "history.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines()]


def test_a_sent_book_is_recorded_in_the_send_history(ks, smtp, setup_done, book, home, capsys):
    run(ks, capsys, "send", "--route", "email", str(book))

    [entry] = history(home)
    assert entry.pop("time")
    assert entry == {"name": "Dune.epub", "size": book.stat().st_size, "route": "email", "result": "sent"}


def test_a_failed_send_is_recorded_with_its_reason(ks, smtp, setup_done, book, home, capsys):
    smtp.login_error = smtplib.SMTPAuthenticationError(535, b"no")

    run(ks, capsys, "send", "--route", "email", str(book))

    [entry] = history(home)
    assert entry["result"] == "failed"
    assert entry["reason"] == "Gmail rejected the app password."


def test_history_time_is_an_iso_timestamp_with_offset(ks, smtp, setup_done, book, home, capsys):
    from datetime import datetime

    run(ks, capsys, "send", "--route", "email", str(book))

    when = datetime.fromisoformat(history(home)[0]["time"])
    assert when.tzinfo is not None


def test_history_drops_entries_older_than_90_days_on_write(ks, smtp, setup_done, book, home, capsys):
    from datetime import datetime, timedelta

    now = datetime.now().astimezone()
    old = {"time": (now - timedelta(days=91)).isoformat(), "name": "Old.pdf", "size": 1,
           "route": "email", "result": "sent"}
    recent = {"time": (now - timedelta(days=89)).isoformat(), "name": "Recent.pdf", "size": 1,
              "route": "email", "result": "sent"}
    path = home / ".local" / "state" / "kindle-send" / "history.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(old) + "\n" + json.dumps(recent) + "\n")

    run(ks, capsys, "send", "--route", "email", str(book))

    assert [e["name"] for e in history(home)] == ["Recent.pdf", "Dune.epub"]


def test_script_runs_as_a_command(home, tmp_path):
    import subprocess
    import sys
    from conftest import SCRIPT

    out = subprocess.run(
        [sys.executable, str(SCRIPT), "send", "--route", "email", str(tmp_path / "Gone.epub")],
        capture_output=True, text=True, check=True,
    )

    assert [json.loads(l) for l in out.stdout.splitlines()] == [
        {"result": "failed", "reason": "File not found: Gone.epub."}
    ]


def test_password_never_in_output_or_tool_arguments(ks, smtp, setup_done, keyring, book, capsys):
    smtp.login_error = smtplib.SMTPAuthenticationError(535, f"bad {PASSWORD}".encode())

    code = ks.main(["send", "--route", "email", str(book)])
    captured = capsys.readouterr()

    assert PASSWORD not in captured.out + captured.err
    assert all(PASSWORD not in call for call in keyring.calls())
