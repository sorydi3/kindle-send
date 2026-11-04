import json
import os

import pytest

from conftest import write_shell_json

KINDLE = "reader@kindle.com"
SENDER = "sender@gmail.com"


def run(ks, capsys, *argv):
    code = ks.main(list(argv))
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    return code, lines


def make_book(path, size=10, mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


@pytest.fixture
def set_up(home):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER)


def test_folders_lists_a_book_in_books_with_its_details(ks, home, set_up, capsys):
    book = make_book(home / "Books" / "Dune.epub", size=1234, mtime=1_700_000_000)

    code, lines = run(ks, capsys, "plan", "--folders")

    assert code == 0
    assert lines == [{
        "path": str(book),
        "name": "Dune.epub",
        "format": "epub",
        "size": 1234,
        "mtime": 1_700_000_000,
        "route": "email",
        "routeReason": "",
        "emailOk": True,
        "usbOk": True,
        "lastSent": None,
    }]


def names(lines):
    return sorted(line["name"] for line in lines)


def test_folders_searches_subfolders_three_levels_deep_and_no_deeper(ks, home, set_up, capsys):
    make_book(home / "Books" / "a" / "b" / "c" / "Deep.pdf")
    make_book(home / "Books" / "a" / "b" / "c" / "d" / "TooDeep.pdf")
    make_book(home / "Downloads" / "Top.txt")

    _, lines = run(ks, capsys, "plan", "--folders")

    assert names(lines) == ["Deep.pdf", "Top.txt"]


def test_folders_skips_hidden_folders_and_unsupported_formats(ks, home, set_up, capsys):
    make_book(home / "Books" / ".cache" / "Hidden.epub")
    make_book(home / "Books" / "Comic.cbz")
    make_book(home / "Books" / "notes")
    make_book(home / "Books" / "Kept.MOBI")

    _, lines = run(ks, capsys, "plan", "--folders")

    assert names(lines) == ["Kept.MOBI"]


def test_folders_lists_newest_first_across_folders(ks, home, set_up, capsys):
    make_book(home / "Books" / "Old.epub", mtime=1_000)
    make_book(home / "Downloads" / "New.pdf", mtime=3_000)
    make_book(home / "Books" / "sub" / "Middle.txt", mtime=2_000)

    _, lines = run(ks, capsys, "plan", "--folders")

    assert [line["name"] for line in lines] == ["New.pdf", "Middle.txt", "Old.epub"]


def test_folders_uses_the_book_folders_setting(ks, home, capsys, tmp_path):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER,
                     bookFolders=["~/Library", str(tmp_path / "elsewhere")])
    make_book(home / "Books" / "NotSearched.epub")
    make_book(home / "Library" / "InLibrary.epub")
    make_book(tmp_path / "elsewhere" / "Elsewhere.pdf")

    _, lines = run(ks, capsys, "plan", "--folders")

    assert names(lines) == ["Elsewhere.pdf", "InLibrary.epub"]


def test_a_book_in_overlapping_folders_is_listed_once(ks, home, capsys):
    write_shell_json(home, kindleAddress=KINDLE, senderAddress=SENDER,
                     bookFolders=["~/Books", "~/Books/sub"])
    make_book(home / "Books" / "sub" / "Dune.epub")

    _, lines = run(ks, capsys, "plan", "--folders")

    assert names(lines) == ["Dune.epub"]


def sparse_book(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.truncate(size)
    return path


def plan_one(ks, capsys, book):
    _, lines = run(ks, capsys, "plan", str(book))
    [line] = lines
    return line


def route_of(line):
    return {k: line[k] for k in ("route", "routeReason", "emailOk", "usbOk")}


def test_a_format_email_cannot_take_goes_by_usb(ks, home, set_up, capsys):
    line = plan_one(ks, capsys, make_book(home / "Books" / "Dune.azw3"))

    assert route_of(line) == {"route": "usb", "routeReason": "AZW3 can't be sent by email.",
                              "emailOk": False, "usbOk": True}


def test_a_format_usb_refuses_goes_by_email(ks, home, set_up, capsys):
    line = plan_one(ks, capsys, make_book(home / "Books" / "Essay.docx"))

    assert route_of(line) == {"route": "email", "routeReason": "",
                              "emailOk": True, "usbOk": False}


def test_email_wins_when_both_routes_work(ks, home, set_up, capsys):
    line = plan_one(ks, capsys, make_book(home / "Books" / "Paper.pdf"))

    assert route_of(line) == {"route": "email", "routeReason": "", "emailOk": True, "usbOk": True}


@pytest.mark.parametrize("size, route", [(26_143_825, "email"), (26_143_826, "usb")])
def test_email_limit_defaults_to_the_estimate_from_gmails_measured_size(ks, home, set_up, capsys, size, route):
    # (35,882,577 - 64 KiB) / 1.37 = 26,143,825.5 bytes
    line = plan_one(ks, capsys, sparse_book(home / "Books" / "Big.pdf", size))

    assert line["route"] == route


def test_a_book_over_the_email_limit_says_why_it_goes_by_usb(ks, home, set_up, capsys):
    line = plan_one(ks, capsys, sparse_book(home / "Books" / "Big.pdf", 40_000_000))

    assert route_of(line) == {"route": "usb", "routeReason": "Too big for email (40 MB).",
                              "emailOk": False, "usbOk": True}


@pytest.mark.parametrize("size, route", [(7_299_270, "email"), (7_299_271, "usb")])
def test_email_limit_uses_the_last_advertised_size(ks, home, set_up, capsys, size, route):
    state = home / ".local" / "state" / "kindle-send"
    state.mkdir(parents=True)
    # (10,065,536 - 65,536) / 1.37 = 7,299,270.07 bytes
    (state / "email-limit.json").write_text(json.dumps({"advertised": 10_065_536}))

    line = plan_one(ks, capsys, sparse_book(home / "Books" / "Big.pdf", size))

    assert line["route"] == route


def test_a_big_book_neither_route_takes_goes_to_usb_and_is_marked_unusable(ks, home, set_up, capsys):
    line = plan_one(ks, capsys, sparse_book(home / "Books" / "Huge.docx", 40_000_000))

    assert route_of(line) == {"route": "usb", "routeReason": "Too big for email (40 MB).",
                              "emailOk": False, "usbOk": False}


def write_history(home, *entries):
    state = home / ".local" / "state" / "kindle-send"
    state.mkdir(parents=True, exist_ok=True)
    (state / "history.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))


def test_last_sent_is_the_latest_successful_send_of_the_same_name_and_size(ks, home, set_up, capsys):
    book = make_book(home / "Books" / "Dune.epub", size=10)
    write_history(
        home,
        {"time": "2026-10-01T10:00:00+01:00", "name": "Dune.epub", "size": 10, "route": "email", "result": "sent"},
        {"time": "2026-10-03T10:00:00+01:00", "name": "Dune.epub", "size": 10, "route": "usb", "result": "copied"},
        {"time": "2026-10-05T10:00:00+01:00", "name": "Dune.epub", "size": 10, "route": "email",
         "result": "failed", "reason": "Couldn't reach Gmail: timed out."},
        {"time": "2026-10-06T10:00:00+01:00", "name": "Dune.epub", "size": 99, "route": "email", "result": "sent"},
        {"time": "2026-10-07T10:00:00+01:00", "name": "Other.epub", "size": 10, "route": "email", "result": "sent"},
    )

    line = plan_one(ks, capsys, book)

    assert line["lastSent"] == "2026-10-03T10:00:00+01:00"


def test_setup_needed_comes_first_and_names_the_missing_settings(ks, home, capsys):
    write_shell_json(home, kindleAddress=KINDLE)
    make_book(home / "Books" / "Dune.epub")

    _, lines = run(ks, capsys, "plan", "--folders")

    assert lines[0] == {"setupNeeded": True, "missing": ["senderAddress"]}
    assert names(lines[1:]) == ["Dune.epub"]


def test_setup_needed_without_any_settings(ks, home, capsys):
    _, lines = run(ks, capsys, "plan", "--folders")

    assert lines == [{"setupNeeded": True, "missing": ["kindleAddress", "senderAddress"]}]


def test_files_are_classified_and_unsupported_or_missing_ones_left_out(ks, home, set_up, capsys, tmp_path):
    pdf = make_book(tmp_path / "anywhere" / "Paper.pdf")
    cbz = make_book(tmp_path / "anywhere" / "Comic.cbz")
    make_book(home / "Books" / "NotAsked.epub")

    _, lines = run(ks, capsys, "plan", str(pdf), str(cbz), str(tmp_path / "gone.epub"))

    assert [line["path"] for line in lines] == [str(pdf)]
