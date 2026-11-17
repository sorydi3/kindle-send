"""`kindle-send settings` and `kindle-send save`: the Settings form's commands (spec §3, §9).

Called in-process through ks.main(), with a temp HOME, the fake `secret-tool`
and stdin replaced by the JSON the Picker would write.
"""
import io
import json
import smtplib
import stat

import pytest

from conftest import read_settings, settings_file, write_settings

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
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Novels", "/srv/books"])
    keyring.set_password("abcd efgh ijkl mnop")

    out = settings(ks, capsys)

    assert out == {"kindleAddress": KINDLE, "senderAddress": SENDER,
                   "bookFolders": ["~/Novels", "/srv/books"], "appPasswordStored": True, "missing": []}


def test_settings_never_prints_the_password(ks, home, keyring, capsys):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER)
    keyring.set_password("abcd efgh ijkl mnop")

    ks.main(["settings"])

    assert "abcd" not in capsys.readouterr().out


def test_settings_with_nothing_set_gives_blanks_and_the_default_folders(ks, home, capsys):
    out = settings(ks, capsys)

    assert out == {"kindleAddress": "", "senderAddress": "",
                   "bookFolders": ["~/Books", "~/Downloads"], "appPasswordStored": False,
                   "missing": ["kindleAddress", "senderAddress", "appPassword"]}


def test_settings_names_a_missing_app_password_once_the_addresses_are_set(ks, home, capsys):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER)

    assert settings(ks, capsys)["missing"] == ["appPassword"]


def save(ks, capsys, monkeypatch, **values):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(values)))
    return run(ks, capsys, ["save"])


def entry(home):
    return read_settings(home)


@pytest.fixture
def folders(home):
    """Book folders that exist, written as the user would type them."""
    (home / "Books").mkdir()
    (home / "Downloads").mkdir()
    return ["~/Books", "~/Downloads"]


@pytest.fixture
def stored(keyring, smtp):
    """An app password already in the keyring, which Gmail accepts, so a save isn't
    blocked for want of one."""
    keyring.set_password("abcd efgh ijkl mnop")
    return keyring


def test_save_writes_the_values_and_keeps_every_other_key(ks, home, folders, stored, capsys, monkeypatch):
    path = write_settings(home, maxEmailsPerHour=5, kindleAddress="old@kindle.com", futureKey={"x": 1})

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "firstSave": True, "problems": []}
    mine = entry(home)
    assert mine["futureKey"] == {"x": 1}
    assert mine["maxEmailsPerHour"] == 5
    assert mine["minEmailGapSeconds"] == 10
    assert mine["kindleAddress"] == KINDLE
    assert mine["senderAddress"] == SENDER
    assert mine["bookFolders"] == ["~/Books", "~/Downloads"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_saved_values_are_what_settings_prints_next(ks, home, folders, stored, capsys, monkeypatch):
    save(ks, capsys, monkeypatch, kindleAddress=" " + KINDLE + " ", senderAddress=SENDER, bookFolders=folders)

    assert settings(ks, capsys)["kindleAddress"] == KINDLE


def test_an_emptied_book_folders_field_saves_as_the_defaults(ks, home, folders, stored, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=[" ", ""])

    assert out["saved"] is True
    assert entry(home)["bookFolders"] == ["~/Books", "~/Downloads"]
    assert settings(ks, capsys)["bookFolders"] == ["~/Books", "~/Downloads"]


@pytest.mark.parametrize("field", ["kindleAddress", "senderAddress"])
def test_an_empty_address_blocks_saving(ks, home, folders, stored, capsys, monkeypatch, field):
    values = {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": folders, field: "  "}

    out = save(ks, capsys, monkeypatch, **values)

    assert out["saved"] is False
    assert out["problems"][0] == {"field": field, "message": "Needed before Books can be sent.", "blocking": True,
                                  "needed": True}
    assert not settings_file(home).exists()


@pytest.mark.parametrize("field", ["kindleAddress", "senderAddress"])
@pytest.mark.parametrize("typed", ["reader", "reader@", "@kindle.com", "two words@kindle.com", "a@b@kindle.com",
                                   "reader@kindle"])
def test_something_that_isnt_an_email_address_blocks_saving(ks, home, folders, stored, capsys, monkeypatch, field, typed):
    write_settings(home, kindleAddress="old@kindle.com", senderAddress="old@gmail.com")
    before = settings_file(home).read_text()
    values = {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": folders, field: typed}

    out = save(ks, capsys, monkeypatch, **values)

    assert out["saved"] is False
    assert out["problems"] == [{"field": field, "message": "That isn't an email address.", "blocking": True}]
    assert settings_file(home).read_text() == before


NEEDED = "Needed before Books can be sent."


def test_without_an_app_password_typed_or_stored_nothing_is_saved(ks, home, folders, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": False, "problems": [
        {"field": "appPassword", "message": NEEDED, "blocking": True, "needed": True}]}
    assert not settings_file(home).exists()


def test_every_missing_value_is_marked_needed_so_the_form_can_count_them(ks, home, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress="", senderAddress="", bookFolders=[])

    assert [(p["field"], p.get("needed")) for p in out["problems"]] == [
        ("kindleAddress", True), ("senderAddress", True), ("appPassword", True)]


def test_a_value_that_isnt_an_address_is_not_a_missing_one(ks, home, folders, keyring, capsys, monkeypatch):
    keyring.set_password(PASSWORD)

    out = save(ks, capsys, monkeypatch, kindleAddress="reader", senderAddress=SENDER, bookFolders=folders)

    assert "needed" not in out["problems"][0]


def test_every_blocking_problem_is_reported_in_form_order(ks, home, folders, stored, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress="", senderAddress="nope", bookFolders=folders)

    assert [(p["field"], p["blocking"]) for p in out["problems"]] == [
        ("kindleAddress", True), ("senderAddress", True)]


@pytest.mark.parametrize("kindle", ["reader@free.kindle.com", "reader@kindle.cn"])
def test_a_kindle_address_not_on_kindle_com_saves_with_a_warning(ks, home, folders, stored, capsys, monkeypatch, kindle):
    out = save(ks, capsys, monkeypatch, kindleAddress=kindle, senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "firstSave": True, "problems": [
        {"field": "kindleAddress", "message": "Kindle addresses usually end in @kindle.com.", "blocking": False}]}
    assert entry(home)["kindleAddress"] == kindle


def test_a_kindle_com_address_in_capitals_needs_no_warning(ks, home, folders, stored, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress="Reader@Kindle.com", senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "firstSave": True, "problems": []}


def test_a_sender_not_on_gmail_com_saves_with_a_warning(ks, home, folders, stored, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress="me@company.example",
               bookFolders=folders)

    assert out == {"saved": True, "firstSave": True, "problems": [
        {"field": "senderAddress", "message": "Make sure this is a Google account.", "blocking": False}]}
    assert entry(home)["senderAddress"] == "me@company.example"


def test_a_book_folder_that_doesnt_exist_saves_with_a_warning_and_isnt_created(ks, home, folders, stored, capsys,
                                                                                monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER,
               bookFolders=["~/Books", "~/Bokos"])

    assert out == {"saved": True, "firstSave": True, "problems": [
        {"field": "bookFolders", "message": "~/Bokos doesn't exist, so the Picker skips it.", "blocking": False}]}
    assert entry(home)["bookFolders"] == ["~/Books", "~/Bokos"]
    assert not (home / "Bokos").exists()


def test_several_missing_book_folders_share_one_warning(ks, home, folders, stored, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER,
               bookFolders=["~/Bokos", "~/Books", "/nowhere"])

    assert out["problems"] == [{"field": "bookFolders", "blocking": False,
                                "message": "~/Bokos and /nowhere don't exist, so the Picker skips them."}]


def test_a_file_is_not_a_book_folder(ks, home, folders, stored, capsys, monkeypatch):
    (home / "notes.txt").write_text("")

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/notes.txt"])

    assert out["problems"][0]["field"] == "bookFolders"


def test_warnings_are_not_given_when_saving_is_blocked(ks, home, capsys, monkeypatch):
    """Only blocking problems while nothing is saved, so the form shows what stops it."""
    out = save(ks, capsys, monkeypatch, kindleAddress="reader@kindle.cn", senderAddress="",
               bookFolders=["~/Bokos"])

    assert out["saved"] is False
    assert [p["field"] for p in out["problems"]] == ["senderAddress", "appPassword"]


def test_unreadable_input_saves_nothing(ks, home, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

    out = run(ks, capsys, ["save"])

    assert out["saved"] is False
    assert out["problems"][0]["blocking"] is True
    assert not settings_file(home).exists()


def test_a_settings_file_that_isnt_valid_json_is_left_alone(ks, home, folders, stored, capsys, monkeypatch):
    settings_file(home).parent.mkdir(parents=True)
    settings_file(home).write_text("{ broken")

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out["saved"] is False
    assert out["problems"] == [{"field": "", "blocking": True,
                                "message": f"{settings_file(home)} isn't valid JSON, so it wasn't changed."}]
    assert settings_file(home).read_text() == "{ broken"


# --- The app password (spec §9, ADR 0001) ------------------------------------

PASSWORD = "abcd efgh ijkl mnop"


def test_a_typed_app_password_is_stored_in_the_keyring_under_the_gmail_address(ks, home, folders, keyring, smtp,
                                                                                capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders,
               appPassword=PASSWORD)

    assert out == {"saved": True, "firstSave": True, "problems": []}
    assert keyring.password() == PASSWORD
    stores = [c for c in keyring.calls() if c.startswith("store")]
    assert len(stores) == 1 and stores[0].endswith("service kindle-send user " + SENDER)
    assert settings(ks, capsys)["appPasswordStored"] is True


def test_the_app_password_never_goes_on_a_command_line_or_into_the_settings_file(ks, home, folders, keyring, smtp,
                                                                          capsys, monkeypatch):
    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders,
         appPassword=PASSWORD)

    assert keyring.calls() and not any("abcd" in c for c in keyring.calls())
    assert "abcd" not in settings_file(home).read_text()


def test_a_typed_app_password_is_checked_by_signing_in_to_gmail_without_sending(ks, home, folders, keyring, smtp,
                                                                                capsys, monkeypatch):
    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders,
         appPassword=PASSWORD)

    [server] = smtp.instances
    assert (server.host, server.port) == ("smtp.gmail.com", 465)
    assert server.logins == [(SENDER, PASSWORD)]
    assert server.sent == []


def rejected(smtp):
    smtp.login_error = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted.")


def test_a_password_gmail_rejects_saves_nothing(ks, home, folders, keyring, smtp, capsys, monkeypatch):
    write_settings(home, kindleAddress="old@kindle.com", senderAddress=SENDER)
    before = settings_file(home).read_text()
    keyring.set_password("old password")
    rejected(smtp)

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders,
               appPassword=PASSWORD)

    assert out == {"saved": False, "problems": [
        {"field": "appPassword", "message": "Gmail rejected this app password.", "blocking": True}]}
    assert settings_file(home).read_text() == before
    assert keyring.password() == "old password"
    assert not any(c.startswith("store") for c in keyring.calls())


@pytest.mark.parametrize("error", [OSError("[Errno 101] Network is unreachable"), TimeoutError("timed out"),
                                   smtplib.SMTPServerDisconnected("Connection unexpectedly closed")])
def test_when_gmail_cant_be_reached_the_password_is_saved_anyway_with_a_warning(ks, home, folders, keyring, smtp,
                                                                                capsys, monkeypatch, error):
    smtp.connect_error = error

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders,
               appPassword=PASSWORD)

    assert out == {"saved": True, "firstSave": True, "problems": [
        {"field": "appPassword", "message": "Couldn't reach Gmail to check the password. Saved anyway.",
         "blocking": False}]}
    assert keyring.password() == PASSWORD
    assert entry(home)["senderAddress"] == SENDER


def test_unchanged_address_and_password_skip_the_check(ks, home, folders, keyring, smtp, capsys, monkeypatch):
    write_settings(home, kindleAddress="old@kindle.com", senderAddress=SENDER)
    keyring.set_password(PASSWORD)

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=" " + SENDER, bookFolders=folders)

    assert out == {"saved": True, "problems": []}
    assert smtp.instances == []
    assert not any(c.startswith("store") for c in keyring.calls())


def test_a_changed_gmail_address_checks_the_password_stored_for_it(ks, home, folders, keyring, smtp, capsys,
                                                                   monkeypatch):
    """The fake keyring holds one password whatever the user, so it stands for the new address's."""
    write_settings(home, kindleAddress=KINDLE, senderAddress="old@gmail.com")
    keyring.set_password(PASSWORD)

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out == {"saved": True, "problems": []}
    assert smtp.instances[0].logins == [(SENDER, PASSWORD)]
    assert "lookup service kindle-send user " + SENDER in keyring.calls()


def test_a_changed_gmail_address_whose_password_gmail_rejects_saves_nothing(ks, home, folders, keyring, smtp,
                                                                            capsys, monkeypatch):
    write_settings(home, kindleAddress=KINDLE, senderAddress="old@gmail.com")
    before = settings_file(home).read_text()
    keyring.set_password(PASSWORD)
    rejected(smtp)

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out["saved"] is False
    assert out["problems"] == [{"field": "appPassword", "message": "Gmail rejected this app password.",
                                "blocking": True}]
    assert settings_file(home).read_text() == before


def test_a_changed_gmail_address_with_no_password_for_it_still_needs_one(ks, home, folders, smtp, capsys,
                                                                         monkeypatch):
    write_settings(home, kindleAddress=KINDLE, senderAddress="old@gmail.com")
    before = settings_file(home).read_text()

    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders)

    assert out["saved"] is False
    assert [p["field"] for p in out["problems"]] == ["appPassword"]
    assert smtp.instances == []
    assert settings_file(home).read_text() == before


def test_a_keyring_that_stores_nothing_saves_nothing(ks, home, folders, smtp, capsys, monkeypatch):
    """No `keyring` fixture: the guard's `secret-tool` fails every call."""
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=folders,
               appPassword=PASSWORD)

    assert out == {"saved": False, "problems": [
        {"field": "appPassword", "message": "Couldn't store the app password in the keyring.", "blocking": True}]}
    assert not settings_file(home).exists()


def test_a_rejected_password_is_never_echoed_back(ks, home, folders, keyring, smtp, capsys, monkeypatch):
    smtp.login_error = smtplib.SMTPAuthenticationError(535, PASSWORD.encode())
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        {"kindleAddress": KINDLE, "senderAddress": SENDER, "bookFolders": folders, "appPassword": PASSWORD})))

    ks.main(["save"])

    assert "abcd" not in capsys.readouterr().out


# --- The first save (spec §9) ---------------------------------------------------

def test_the_first_save_creates_books(ks, home, keyring, smtp, capsys, monkeypatch):
    out = save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Books"],
               appPassword=PASSWORD)

    assert out == {"saved": True, "firstSave": True, "problems": []}
    assert (home / "Books").is_dir()


def test_the_first_save_creates_books_even_when_it_isnt_a_book_folder(ks, home, keyring, smtp, capsys,
                                                                     monkeypatch):
    (home / "Novels").mkdir()

    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Novels"],
         appPassword=PASSWORD)

    assert (home / "Books").is_dir()


def test_a_save_once_set_up_never_creates_books(ks, home, stored, capsys, monkeypatch):
    write_settings(home, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Books"])

    out = save(ks, capsys, monkeypatch, kindleAddress="other@kindle.com", senderAddress=SENDER,
               bookFolders=["~/Books"])

    assert out["saved"] is True
    assert "firstSave" not in out
    assert not (home / "Books").exists()


def test_a_blocked_first_save_creates_nothing(ks, home, capsys, monkeypatch):
    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Books"])

    assert not (home / "Books").exists()


def test_once_saved_nothing_is_missing(ks, home, keyring, smtp, capsys, monkeypatch):
    save(ks, capsys, monkeypatch, kindleAddress=KINDLE, senderAddress=SENDER, bookFolders=["~/Books"],
         appPassword=PASSWORD)

    assert settings(ks, capsys)["missing"] == []
