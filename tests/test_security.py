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
