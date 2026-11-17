"""Settings live in their own file (spec §9, ADR 0002).

`~/.config/kindle-send/settings.json` ($XDG_CONFIG_HOME), mode 600, written
atomically by kindle-send only. A one-time copy from the plugin's old
`shell.json` entry; `shell.json` itself is never written.
"""
import io
import json
import stat

import pytest

from conftest import read_settings, settings_file, shell_json, write_settings, write_shell_json

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"
PASSWORD = "abcd efgh ijkl mnop"


def save(ks, monkeypatch, **values):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(values)))
    assert ks.main(["save"]) == 0


def printed(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


@pytest.fixture
def stored(keyring, smtp):
    keyring.set_password(PASSWORD)
    return keyring


def test_save_writes_the_settings_file_with_mode_600(ks, home, stored, capsys, monkeypatch):
    save(ks, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Books"])

    assert printed(capsys)[0]["saved"] is True
    assert read_settings(home) == {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": ["~/Books"],
                                   "minEmailGapSeconds": 10, "maxEmailsPerHour": 20}
    assert stat.S_IMODE(settings_file(home).stat().st_mode) == 0o600
    assert not shell_json(home).exists()


# --- The one-time copy from shell.json ------------------------------------------

def old_entry(home, **extra):
    """The plugin's old shell.json entry, with omarchy's own keys beside the Settings."""
    return write_shell_json(home, enabled=True, kindleAddress=KINDLE, senderAddress=SENDER,
                            bookFolders=["~/Novels"], minEmailGapSeconds=30, maxEmailsPerHour=5, **extra)


def test_the_first_run_copies_settings_from_the_old_shell_json_entry(ks, home, stored, capsys):
    old_entry(home)

    ks.main(["settings"])

    assert read_settings(home) == {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": ["~/Novels"],
                                   "minEmailGapSeconds": 30, "maxEmailsPerHour": 5}
    assert stat.S_IMODE(settings_file(home).stat().st_mode) == 0o600
    assert printed(capsys)[0]["bookFolders"] == ["~/Novels"]


def test_once_copied_shell_json_is_never_read_again(ks, home, stored, capsys):
    old_entry(home)
    ks.main(["settings"])
    write_shell_json(home, kindleAddress="changed@kindle.com", senderAddress=SENDER)
    capsys.readouterr()

    ks.main(["settings"])

    assert printed(capsys)[0]["kindleAddress"] == KINDLE


def test_an_existing_settings_file_wins_over_shell_json(ks, home, stored, capsys):
    write_settings(home, kindleAddress="mine@kindle.com", senderAddress=SENDER)
    old_entry(home)

    ks.main(["settings"])

    assert printed(capsys)[0]["kindleAddress"] == "mine@kindle.com"
    assert read_settings(home) == {"kindleAddress": "mine@kindle.com", "senderAddress": SENDER}


def test_an_entry_without_settings_copies_nothing(ks, home, capsys):
    write_shell_json(home, enabled=True)

    ks.main(["settings"])

    assert not settings_file(home).exists()


def test_a_settings_file_that_isnt_valid_json_is_not_replaced_by_the_copy(ks, home, stored, capsys):
    settings_file(home).parent.mkdir(parents=True)
    settings_file(home).write_text("{ broken")
    old_entry(home)

    ks.main(["settings"])

    assert settings_file(home).read_text() == "{ broken"
    assert printed(capsys)[0]["kindleAddress"] == ""


def test_save_after_the_copy_keeps_the_copied_send_limit_numbers(ks, home, stored, capsys, monkeypatch):
    old_entry(home)

    save(ks, monkeypatch, kindleAddress="new@kindle.com", senderAddress=SENDER, bookFolders=["~/Books"])

    saved = read_settings(home)
    assert saved["kindleAddress"] == "new@kindle.com"
    assert (saved["minEmailGapSeconds"], saved["maxEmailsPerHour"]) == (30, 5)


# --- shell.json is never written ---------------------------------------------------

class FakeTerminal(io.StringIO):
    def isatty(self):
        return True


def run_save(ks, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        {"kindleAddress": "new@kindle.com", "senderAddress": SENDER, "bookFolders": ["~/Books"]})))
    return ks.main(["save"])


def run_setup(ks, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.stdin", FakeTerminal("new@kindle.com\n\n\n\n\nn\n"))
    return ks.main(["setup"])


def run_send(ks, monkeypatch, tmp_path):
    book = tmp_path / "Dune.epub"
    book.write_bytes(b"epub")
    return ks.main(["send", "--route", "email", str(book)])


COMMANDS = {
    "settings": lambda ks, mp, tmp: ks.main(["settings"]),
    "save": run_save,
    "plan": lambda ks, mp, tmp: ks.main(["plan", "--folders"]),
    "send": run_send,
    "send --test": lambda ks, mp, tmp: ks.main(["send", "--route", "email", "--test"]),
    "setup": run_setup,
    "limit": lambda ks, mp, tmp: ks.main(["limit"]),
}


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("copied", [False, True], ids=["first run", "after the copy"])
def test_shell_json_is_left_untouched(ks, home, stored, capsys, monkeypatch, tmp_path, command, copied):
    path = old_entry(home)
    if copied:
        ks.main(["settings"])
    before = (path.read_bytes(), path.stat().st_mtime_ns, stat.S_IMODE(path.stat().st_mode))

    COMMANDS[command](ks, monkeypatch, tmp_path)

    assert (path.read_bytes(), path.stat().st_mtime_ns, stat.S_IMODE(path.stat().st_mode)) == before
    assert sorted(p.name for p in path.parent.iterdir()) == ["shell.json"]


def test_save_and_setup_never_create_shell_json(ks, home, stored, capsys, monkeypatch, tmp_path):
    run_save(ks, monkeypatch, tmp_path)
    run_setup(ks, monkeypatch, tmp_path)

    assert read_settings(home)["kindleAddress"] == "new@kindle.com"
    assert not shell_json(home).parent.exists()


# --- Writing the file ----------------------------------------------------------------

def test_saving_over_a_readable_file_makes_it_private_and_leaves_no_temp_file(ks, home, stored, capsys,
                                                                             monkeypatch):
    path = write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER, maxEmailsPerHour=3)
    path.chmod(0o644)

    save(ks, monkeypatch, kindleAddress="new@kindle.com", senderAddress=SENDER, bookFolders=["~/Books"])

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert read_settings(home)["maxEmailsPerHour"] == 3
    assert [p.name for p in path.parent.iterdir()] == ["settings.json"]


def test_the_settings_file_follows_xdg_config_home(ks, home, stored, capsys, monkeypatch, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(elsewhere))

    save(ks, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Books"])

    assert json.loads((elsewhere / "kindle-send" / "settings.json").read_text())["kindleAddress"] == KINDLE
    assert not settings_file(home).exists()


def test_the_wizard_says_where_it_saved(ks, home, stored, capsys, monkeypatch, tmp_path):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER)

    run_setup(ks, monkeypatch, tmp_path)

    assert f"Settings saved to {settings_file(home)}." in capsys.readouterr().out
