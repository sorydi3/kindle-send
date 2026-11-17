"""`kindle-send setup`: the interactive wizard (spec §9).

Driven in-process through ks.main(["setup"]) with a fake terminal on stdin,
the fake `secret-tool` and the fake SMTP from conftest.
"""
import io
import json

import pytest

from conftest import read_settings, settings_file, write_settings

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"


class FakeTerminal(io.StringIO):
    """Typed answers, one per line; reports itself as a TTY."""

    def isatty(self):
        return True


@pytest.fixture(autouse=True)
def no_real_gmail(smtp):
    """Every setup test gets the fake SMTP, so a stray test send can't reach Gmail."""


@pytest.fixture
def terminal(monkeypatch):
    def type_lines(*answers):
        monkeypatch.setattr("sys.stdin", FakeTerminal("".join(a + "\n" for a in answers)))
    return type_lines


def test_refuses_to_run_without_a_terminal(ks, keyring, home, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(KINDLE + "\n" + SENDER + "\n"))

    code = ks.main(["setup"])

    assert code != 0
    assert "terminal" in capsys.readouterr().err
    assert keyring.calls() == []
    assert not settings_file(home).exists()


def plugin_entry(home):
    return read_settings(home)


def test_first_run_saves_settings_and_stores_the_password(ks, keyring, home, terminal, capsys):
    keyring.will_type("abcd efgh ijkl mnop")
    terminal(KINDLE, SENDER, "", "", "n")  # Kindle, Gmail, approved Enter, folders Enter, no test send

    code = ks.main(["setup"])

    assert code == 0
    entry = plugin_entry(home)
    assert entry["kindleAddress"] == KINDLE
    assert entry["senderAddress"] == SENDER
    assert entry["bookFolders"] == ["~/Books", "~/Downloads"]
    assert entry["minEmailGapSeconds"] == 10
    assert entry["maxEmailsPerHour"] == 20
    assert keyring.password() == "abcd efgh ijkl mnop"
    store_calls = [c for c in keyring.calls() if c.startswith("store")]
    assert len(store_calls) == 1
    assert store_calls[0].endswith("service kindle-send user " + SENDER)
    out = capsys.readouterr().out
    assert "abcd efgh" not in out


def test_keeps_other_keys_and_makes_the_file_private(ks, keyring, home, terminal):
    path = write_settings(home, maxEmailsPerHour=5, futureKey={"x": 1})
    path.chmod(0o644)
    keyring.will_type("pw")
    terminal(KINDLE, SENDER, "", "", "n")

    assert ks.main(["setup"]) == 0

    entry = plugin_entry(home)
    assert entry["futureKey"] == {"x": 1}
    assert entry["maxEmailsPerHour"] == 5
    assert entry["kindleAddress"] == KINDLE
    assert path.stat().st_mode & 0o777 == 0o600


def test_refuses_to_overwrite_a_settings_file_it_cannot_parse(ks, keyring, home, terminal, capsys):
    path = settings_file(home)
    path.parent.mkdir(parents=True)
    path.write_text("{ not json")
    keyring.will_type("pw")
    terminal(KINDLE, SENDER, "", "", "n")

    assert ks.main(["setup"]) != 0

    assert path.read_text() == "{ not json"
    assert f"{path} isn't valid JSON" in capsys.readouterr().out


def test_creates_books_folder_when_missing(ks, keyring, home, terminal):
    keyring.will_type("pw")
    terminal(KINDLE, SENDER, "", "", "n")

    ks.main(["setup"])

    assert (home / "Books").is_dir()


def test_steps_run_in_spec_order_with_help_links(ks, keyring, home, terminal, capsys):
    keyring.will_type("pw")
    terminal(KINDLE, SENDER, "", "", "n")

    ks.main(["setup"])

    out = capsys.readouterr().out
    markers = [
        "Manage Your Content and Devices",
        "Gmail address",
        "https://myaccount.google.com/apppasswords",
        "Add " + SENDER + " to Amazon's Approved Personal Document Email List",
        "Book folders",
        "Test send",
    ]
    positions = [out.index(m) for m in markers]
    assert positions == sorted(positions)
    assert "https://www.amazon.com/mycd" in out


def test_rerun_shows_current_values_and_enter_keeps_everything(ks, keyring, home, terminal, capsys):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER,
                     bookFolders=["~/Books", "~/Papers"])
    keyring.set_password("old password")
    terminal("", "", "", "", "", "n")  # Kindle, Gmail, keep password, approved, folders, no test

    assert ks.main(["setup"]) == 0

    entry = plugin_entry(home)
    assert entry["kindleAddress"] == KINDLE
    assert entry["senderAddress"] == SENDER
    assert entry["bookFolders"] == ["~/Books", "~/Papers"]
    assert keyring.password() == "old password"
    assert not [c for c in keyring.calls() if c.startswith("store")]
    out = capsys.readouterr().out
    assert "[" + KINDLE + "]" in out
    assert "[" + SENDER + "]" in out
    assert "[~/Books, ~/Papers]" in out
    assert "old password" not in out


def test_rerun_with_a_new_gmail_address_asks_for_its_password(ks, keyring, home, terminal):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER)
    keyring.will_type("new pw")
    terminal("", "other@gmail.com", "", "", "n")

    assert ks.main(["setup"]) == 0

    stores = [c for c in keyring.calls() if c.startswith("store")]
    assert len(stores) == 1
    assert stores[0].endswith("user other@gmail.com")


def test_an_empty_password_is_not_accepted(ks, keyring, home, terminal, capsys):
    keyring.will_type("")
    terminal(KINDLE, SENDER)  # then the user gives up (end of input)

    assert ks.main(["setup"]) != 0

    assert "Nothing was stored" in capsys.readouterr().out
    assert not settings_file(home).exists()


def test_test_send_emails_the_bundled_epub_and_asks_if_it_arrived(ks, keyring, smtp, home, terminal, capsys):
    keyring.will_type("pw")
    terminal(KINDLE, SENDER, "", "", "y", "y")

    assert ks.main(["setup"]) == 0

    [server] = smtp.instances
    [msg] = server.sent
    assert msg["To"] == KINDLE
    assert msg["From"] == SENDER
    assert msg["Subject"] == "Kindle Send Test"
    [attachment] = list(msg.iter_attachments())
    assert attachment.get_filename() == "Kindle Send Test.epub"
    assert attachment.get_content_type() == "application/epub+zip"
    out = capsys.readouterr().out
    assert "Did 'Kindle Send Test' appear on your Kindle within a few minutes?" in out
    assert '{"stage"' not in out


def test_test_send_that_never_arrived_lists_the_usual_causes(ks, keyring, smtp, home, terminal, capsys):
    keyring.will_type("pw")
    terminal(KINDLE, SENDER, "", "", "y", "n")

    assert ks.main(["setup"]) == 0

    out = capsys.readouterr().out.split("within a few minutes?")[1]
    assert "Approved Personal Document Email List" in out
    assert KINDLE in out


def test_failed_test_send_shows_the_reason_and_does_not_ask(ks, keyring, smtp, home, terminal, capsys):
    import smtplib
    smtp.login_error = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    keyring.will_type("wrong")
    terminal(KINDLE, SENDER, "", "", "y")

    assert ks.main(["setup"]) == 0

    out = capsys.readouterr().out
    assert "Gmail rejected the app password." in out
    assert "appear on your Kindle" not in out


def test_bundled_test_epub_is_a_minimal_valid_epub(ks):
    import zipfile
    from pathlib import Path
    epub = Path(ks.__file__).resolve().parent.parent / "assets" / "test.epub"

    with zipfile.ZipFile(epub) as z:
        first = z.infolist()[0]
        assert first.filename == "mimetype"
        assert first.compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype") == b"application/epub+zip"
        container = z.read("META-INF/container.xml").decode()
        opf_path = container.split('full-path="')[1].split('"')[0]
        opf = z.read(opf_path).decode()
        assert "<dc:title>Kindle Send Test</dc:title>" in opf
