"""`kindle-send settings` and `kindle-send save`: the Settings form's commands (spec §3, §9).

Called in-process through ks.main(), with a temp HOME, the fake `secret-tool`
and stdin replaced by the JSON the Picker would write.
"""
import io
import json
import stat

import pytest

from conftest import write_shell_json

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"


def run(ks, capsys, argv):
    code = ks.main(argv)
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert code == 0
    assert len(lines) == 1
    return lines[0]


def settings(ks, capsys):
    return run(ks, capsys, ["settings"])


def test_settings_prints_the_current_values_with_folders_as_written(ks, home, keyring, capsys):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Novels", "/srv/books"])
    keyring.set_password("abcd efgh ijkl mnop")

    out = settings(ks, capsys)

    assert out == {"kindleAddress": KINDLE, "senderAddress": SENDER,
                   "bookFolders": ["~/Novels", "/srv/books"], "appPasswordStored": True}


def test_settings_never_prints_the_password(ks, home, keyring, capsys):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER)
    keyring.set_password("abcd efgh ijkl mnop")

    ks.main(["settings"])

    assert "abcd" not in capsys.readouterr().out


def test_settings_with_nothing_set_gives_blanks_and_the_default_folders(ks, home, capsys):
    out = settings(ks, capsys)

    assert out == {"kindleAddress": "", "senderAddress": "",
                   "bookFolders": ["~/Books", "~/Downloads"], "appPasswordStored": False}


def save(ks, capsys, monkeypatch, **values):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(values)))
    return run(ks, capsys, ["save"])


def entry(home):
    data = json.loads((home / ".config" / "omarchy" / "shell.json").read_text())
    [mine] = [p for p in data["plugins"] if p.get("id") == "sorydi3.kindle-send"]
    return data, mine


@pytest.fixture
def folders(home):
    """Book folders that exist, written as the user would type them."""
    (home / "Books").mkdir()
    (home / "Downloads").mkdir()
    return ["~/Books", "~/Downloads"]


def test_save_writes_the_values_and_keeps_every_other_key(ks, home, folders, capsys, monkeypatch):
    path = home / ".config" / "omarchy" / "shell.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "theme": {"accent": "blue"},
        "plugins": [{"id": "other.plugin", "x": 1},
                    {"id": "sorydi3.kindle-send", "enabled": True, "maxEmailsPerHour": 5,
                     "kindleAddress": "old@kindle.com"}]}))

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "problems": []}
    data, mine = entry(home)
    assert data["theme"] == {"accent": "blue"}
    assert {"id": "other.plugin", "x": 1} in data["plugins"]
    assert mine["enabled"] is True
    assert mine["maxEmailsPerHour"] == 5
    assert mine["kindleAddress"] == KINDLE
    assert mine["senderAddress"] == SENDER
    assert mine["bookFolders"] == ["~/Books", "~/Downloads"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_saved_values_are_what_settings_prints_next(ks, home, folders, capsys, monkeypatch):
    save(ks, capsys, monkeypatch, kindleAddress=" " + KINDLE + " ", senderAddress=SENDER, bookFolders=folders)

    assert settings(ks, capsys)["kindleAddress"] == KINDLE


def test_an_emptied_book_folders_field_saves_as_the_defaults(ks, home, folders, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=[" ", ""])

    assert out["saved"] is True
    assert entry(home)[1]["bookFolders"] == ["~/Books", "~/Downloads"]
    assert settings(ks, capsys)["bookFolders"] == ["~/Books", "~/Downloads"]


def shell_json(home):
    return home / ".config" / "omarchy" / "shell.json"


@pytest.mark.parametrize("field", ["kindleAddress", "senderAddress"])
def test_an_empty_address_blocks_saving(ks, home, folders, capsys, monkeypatch, field):
    values = {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": folders, field: "  "}

    out = save(ks, capsys, monkeypatch, **values)

    assert out["saved"] is False
    assert out["problems"] == [{"field": field, "message": "Needed before Books can be sent.", "blocking": True}]
    assert not shell_json(home).exists()


@pytest.mark.parametrize("field", ["kindleAddress", "senderAddress"])
@pytest.mark.parametrize("typed", ["reader", "reader@", "@kindle.com", "two words@kindle.com", "a@b@kindle.com",
                                   "reader@kindle"])
def test_something_that_isnt_an_email_address_blocks_saving(ks, home, folders, capsys, monkeypatch, field, typed):
    write_shell_json(home, kindleAddress="old@kindle.com", senderAddress="old@gmail.com")
    before = shell_json(home).read_text()
    values = {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": folders, field: typed}

    out = save(ks, capsys, monkeypatch, **values)

    assert out["saved"] is False
    assert out["problems"] == [{"field": field, "message": "That isn't an email address.", "blocking": True}]
    assert shell_json(home).read_text() == before


def test_every_blocking_problem_is_reported_in_form_order(ks, home, folders, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress="", senderAddress="nope", bookFolders=folders)

    assert [(p["field"], p["blocking"]) for p in out["problems"]] == [
        ("kindleAddress", True), ("senderAddress", True)]


@pytest.mark.parametrize("kindle", ["reader@free.kindle.com", "reader@kindle.cn"])
def test_a_kindle_address_not_on_kindle_com_saves_with_a_warning(ks, home, folders, capsys, monkeypatch, kindle):
    out = save(ks, capsys, monkeypatch, kindleAddress=kindle, senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "problems": [
        {"field": "kindleAddress", "message": "Kindle addresses usually end in @kindle.com", "blocking": False}]}
    assert entry(home)[1]["kindleAddress"] == kindle


def test_a_kindle_com_address_in_capitals_needs_no_warning(ks, home, folders, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress="Reader@Kindle.com", senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "problems": []}


def test_a_sender_not_on_gmail_com_saves_with_a_warning(ks, home, folders, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress="me@company.example",
               bookFolders=folders)

    assert out == {"saved": True, "problems": [
        {"field": "senderAddress", "message": "Make sure this is a Google account", "blocking": False}]}
    assert entry(home)[1]["senderAddress"] == "me@company.example"


def test_a_book_folder_that_doesnt_exist_saves_with_a_warning_and_isnt_created(ks, home, folders, capsys,
                                                                                monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER,
               bookFolders=["~/Books", "~/Bokos"])

    assert out == {"saved": True, "problems": [
        {"field": "bookFolders", "message": "~/Bokos doesn't exist, so the Picker skips it", "blocking": False}]}
    assert entry(home)[1]["bookFolders"] == ["~/Books", "~/Bokos"]
    assert not (home / "Bokos").exists()


def test_several_missing_book_folders_share_one_warning(ks, home, folders, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER,
               bookFolders=["~/Bokos", "~/Books", "/nowhere"])

    assert out["problems"] == [{"field": "bookFolders", "blocking": False,
                                "message": "~/Bokos and /nowhere don't exist, so the Picker skips them"}]


def test_a_file_is_not_a_book_folder(ks, home, folders, capsys, monkeypatch):
    (home / "notes.txt").write_text("")

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/notes.txt"])

    assert out["problems"][0]["field"] == "bookFolders"


def test_warnings_are_not_given_when_saving_is_blocked(ks, home, capsys, monkeypatch):
    """Only blocking problems while nothing is saved, so the form shows what stops it."""
    out = save(ks, capsys, monkeypatch, kindleAddress="reader@kindle.cn", senderAddress="",
               bookFolders=["~/Bokos"])

    assert out["saved"] is False
    assert [p["field"] for p in out["problems"]] == ["senderAddress"]


def test_unreadable_input_saves_nothing(ks, home, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

    out = run(ks, capsys, ["save"])

    assert out["saved"] is False
    assert out["problems"][0]["blocking"] is True
    assert not shell_json(home).exists()


def test_a_shell_json_that_isnt_valid_json_is_left_alone(ks, home, folders, capsys, monkeypatch):
    shell_json(home).parent.mkdir(parents=True)
    shell_json(home).write_text("{ broken")

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out["saved"] is False
    assert out["problems"] == [{"field": "", "blocking": True,
                                "message": f"{shell_json(home)} isn't valid JSON, so it wasn't changed."}]
    assert shell_json(home).read_text() == "{ broken"
