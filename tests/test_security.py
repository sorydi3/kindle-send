"""Fixes from the marketplace security review: Gmail's certificate is verified,
the Send history and the other files kindle-send keeps are private, and a USB
copy never writes through a link.

In-process through ks.main(), with a temp HOME, the fake SMTP, the fake
`secret-tool` and a fake Kindle mounted on a temp dir.
"""
import io
import json
import os
import ssl
import stat

import pytest

from conftest import write_settings

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"
PASSWORD = "abcd efgh ijkl mnop"
CERT_DETAIL = "self-signed certificate"
CERT_ERROR = ssl.SSLCertVerificationError(
    1, f"[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: {CERT_DETAIL} (_ssl.c:1010)")
CERT_ERROR.verify_message = CERT_DETAIL


def run(ks, capsys, *argv):
    code = ks.main(list(argv))
    return code, [json.loads(l) for l in capsys.readouterr().out.splitlines()]


def save(ks, capsys, monkeypatch, **form):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(form)))
    ks.main(["save"])
    return json.loads(capsys.readouterr().out)


def mode(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.fixture
def book(tmp_path):
    path = tmp_path / "Dune.epub"
    path.write_bytes(b"PK\x03\x04 tiny epub")
    return path


@pytest.fixture
def setup_done(home, keyring):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER)
    keyring.set_password(PASSWORD + "\n")


def assert_verifies(server):
    assert isinstance(server.context, ssl.SSLContext)
    assert server.context.verify_mode == ssl.CERT_REQUIRED
    assert server.context.check_hostname is True
    assert server.timeout == 60


# --- Gmail's certificate --------------------------------------------------------------

def test_sending_verifies_gmails_certificate_and_hostname(ks, smtp, setup_done, book, capsys):
    run(ks, capsys, "send", "--route", "email", str(book))

    [server] = smtp.instances
    assert_verifies(server)


def test_a_certificate_gmail_cant_prove_fails_the_send_and_says_so(ks, smtp, setup_done, book, capsys):
    smtp.connect_error = CERT_ERROR

    _, lines = run(ks, capsys, "send", "--route", "email", str(book))

    assert lines[-1] == {"result": "failed", "code": "gmail_certificate_invalid",
                         "values": {"detail": CERT_DETAIL},
                         "reason": f"Couldn't verify Gmail's certificate: {CERT_DETAIL}."}


def test_checking_a_password_verifies_gmails_certificate_and_hostname(ks, home, keyring, smtp, capsys,
                                                                       monkeypatch, tmp_path):
    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=[str(tmp_path)],
         appPassword=PASSWORD)

    [server] = smtp.instances
    assert_verifies(server)


def test_a_certificate_failure_while_checking_a_password_is_named_not_hidden(ks, home, keyring, smtp, capsys,
                                                                              monkeypatch, tmp_path):
    smtp.connect_error = CERT_ERROR

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER,
               bookFolders=[str(tmp_path)], appPassword=PASSWORD)

    assert out["problems"] == [
        {"field": "appPassword", "code": "password_check_untrusted", "values": {"detail": CERT_DETAIL},
         "message": f"Couldn't verify Gmail's certificate, so the password wasn't checked: {CERT_DETAIL}. "
                    "Saved anyway.", "blocking": False}]


# --- Private state and config files -----------------------------------------------------

def state(home):
    return home / ".local" / "state" / "kindle-send"


def config(home):
    return home / ".config" / "kindle-send"


@pytest.fixture
def kindle(usb, tmp_path):
    mount = usb.plug(tmp_path / "Kindle")
    (mount / "documents").mkdir()
    return mount


def usb_send(ks, capsys, tmp_path, name="Atlas.pdf"):
    book = tmp_path / name
    book.write_bytes(b"%PDF-1.7 atlas")
    return run(ks, capsys, "send", "--route", "usb", str(book))


def test_the_send_history_is_readable_only_by_its_owner(ks, home, kindle, tmp_path, capsys):
    usb_send(ks, capsys, tmp_path)

    assert mode(state(home)) == 0o700
    assert mode(state(home) / "history.jsonl") == 0o600


def test_an_existing_open_state_folder_and_history_are_tightened(ks, home, kindle, tmp_path, capsys):
    state(home).mkdir(parents=True)
    state(home).chmod(0o755)
    history = state(home) / "history.jsonl"
    history.write_text('{"time": "2026-11-18T10:00:00+00:00", "name": "Old.pdf", "size": 1, '
                       '"route": "usb", "result": "copied"}\n')
    history.chmod(0o644)

    usb_send(ks, capsys, tmp_path)

    assert mode(state(home)) == 0o700
    assert mode(history) == 0o600
    assert [e["name"] for e in ks.read_history()] == ["Old.pdf", "Atlas.pdf"]


def test_the_cached_email_limit_is_private_too(ks, home, smtp, setup_done, book, capsys):
    run(ks, capsys, "send", "--route", "email", str(book))

    assert mode(state(home)) == 0o700
    assert mode(state(home) / "email-limit.json") == 0o600


def test_a_link_left_where_the_history_is_written_is_replaced_not_followed(ks, home, kindle, tmp_path, capsys):
    state(home).mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("untouched\n")
    (state(home) / "history.jsonl.tmp").symlink_to(elsewhere)

    usb_send(ks, capsys, tmp_path)

    assert elsewhere.read_text() == "untouched\n"
    assert [e["name"] for e in ks.read_history()] == ["Atlas.pdf"]


def test_the_settings_folder_is_private_and_an_open_one_is_tightened(ks, home, keyring, smtp, capsys,
                                                                       monkeypatch, tmp_path):
    config(home).mkdir(parents=True)
    config(home).chmod(0o755)

    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=[str(tmp_path)],
         appPassword=PASSWORD)

    assert mode(config(home)) == 0o700
    assert mode(config(home) / "settings.json") == 0o600


# --- The USB copy never writes through a link -------------------------------------------

def test_a_link_where_the_staging_file_goes_is_removed_not_written_through(ks, kindle, tmp_path, capsys):
    outside = tmp_path / "outside.txt"
    outside.write_text("untouched\n")
    (kindle / "documents" / ".Atlas.pdf.part").symlink_to(outside)

    _, lines = usb_send(ks, capsys, tmp_path)

    assert lines[-1] == {"result": "copied"}
    assert outside.read_text() == "untouched\n"
    assert (kindle / "documents" / "Atlas.pdf").read_bytes() == b"%PDF-1.7 atlas"
    assert not (kindle / "documents" / "Atlas.pdf").is_symlink()
    assert sorted(p.name for p in (kindle / "documents").iterdir()) == ["Atlas.pdf"]


def test_a_documents_folder_that_links_off_the_kindle_is_refused(ks, usb, tmp_path, capsys):
    mount = usb.plug(tmp_path / "Kindle")
    outside = tmp_path / "outside"
    outside.mkdir()
    (mount / "documents").symlink_to(outside)

    _, lines = usb_send(ks, capsys, tmp_path)

    detail = "documents links outside the Kindle"
    assert lines[-1] == {"result": "failed", "code": "copy_failed", "values": {"detail": detail},
                         "reason": f"Couldn't copy to the Kindle: {detail}."}
    assert list(outside.iterdir()) == []


def test_a_documents_link_that_points_nowhere_is_refused_without_a_crash(ks, usb, tmp_path, capsys):
    mount = usb.plug(tmp_path / "Kindle")
    (mount / "documents").symlink_to(tmp_path / "gone")

    _, lines = usb_send(ks, capsys, tmp_path)

    assert lines[-1]["code"] == "copy_failed"
    assert not (tmp_path / "gone").exists()


def test_a_documents_link_that_stays_on_the_kindle_is_followed(ks, usb, tmp_path, capsys):
    mount = usb.plug(tmp_path / "Kindle")
    (mount / "Books").mkdir()
    (mount / "documents").symlink_to("Books")

    _, lines = usb_send(ks, capsys, tmp_path)

    assert lines[-1] == {"result": "copied"}
    assert (mount / "Books" / "Atlas.pdf").read_bytes() == b"%PDF-1.7 atlas"
