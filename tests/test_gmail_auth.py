"""Gmail answers a wrong app password with 535 and then hangs up (seen on the real
account, 2026-11-05). smtplib's login() would go on to try AUTH LOGIN on the dead
connection and report "Connection unexpectedly closed", hiding the rejection.

Runs a real SMTP conversation against a tiny server on 127.0.0.1; nothing leaves the machine.
"""
import json
import smtplib
import socket
import threading

import pytest

from test_send_email import book, setup_done  # noqa: F401

# The autouse guard replaces smtplib.SMTP; LMTP's base is the real class.
REAL_SMTP = smtplib.LMTP.__bases__[0]


@pytest.fixture
def gmail_that_hangs_up():
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    commands = []

    def serve():
        conn, _ = listener.accept()
        with conn, conn.makefile("rb") as lines:
            conn.sendall(b"220 fake ESMTP\r\n")
            for raw in lines:
                line = raw.decode().strip()
                commands.append(line.split(" ")[0] + (" " + line.split(" ")[1] if line.startswith("AUTH") else ""))
                if line.upper().startswith("EHLO"):
                    conn.sendall(b"250-fake\r\n250-SIZE 35882577\r\n250 AUTH LOGIN PLAIN XOAUTH2\r\n")
                elif line.upper().startswith("AUTH"):
                    conn.sendall(b"535 5.7.8 Username and Password not accepted.\r\n")
                    return  # hang up, as Gmail does
                else:
                    conn.sendall(b"250 ok\r\n")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield port, commands
    listener.close()
    thread.join(timeout=5)


def test_a_rejected_password_is_reported_even_when_gmail_hangs_up(ks, keyring, setup_done, book,
                                                                   gmail_that_hangs_up, monkeypatch, capsys):
    port, commands = gmail_that_hangs_up
    monkeypatch.setattr(ks.smtplib, "SMTP_SSL", lambda host, _port, **kw: REAL_SMTP("127.0.0.1", port, **kw))

    ks.main(["send", "--route", "email", str(book)])

    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result == {"result": "failed", "reason": "Gmail rejected the app password.", "fixBySetup": True}
    assert commands[-1] == "AUTH PLAIN"
