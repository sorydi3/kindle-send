"""`kindle-send history`: the last 20 Sends, human-readable (spec §12)."""
import json
import time

import pytest


@pytest.fixture
def utc(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def write_history(home, *entries):
    state = home / ".local" / "state" / "kindle-send"
    state.mkdir(parents=True, exist_ok=True)
    (state / "history.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))


def entry(time, name, route="email", result="sent", **extra):
    return {"time": time, "name": name, "size": 10, "route": route, "result": result, **extra}


def history_lines(ks, capsys):
    code = ks.main(["history"])
    assert code == 0
    return capsys.readouterr().out.splitlines()


def test_history_prints_a_sent_book_like_the_spec_example(ks, home, utc, capsys):
    write_history(home, entry("2026-11-04T23:17:05+00:00", "Dune.epub"))

    assert history_lines(ks, capsys) == ["Nov 4 23:17 · Dune.epub · Email · Sent to Amazon"]


def test_history_labels_usb_copies_and_failures_with_their_reason(ks, home, utc, capsys):
    write_history(
        home,
        entry("2026-11-01T09:05:00+00:00", "Big.pdf", route="usb", result="copied"),
        entry("2026-11-02T10:00:00+00:00", "Dune.epub", result="failed",
              reason="Gmail rejected the app password."),
    )

    assert history_lines(ks, capsys) == [
        "Nov 2 10:00 · Dune.epub · Email · Failed: Gmail rejected the app password.",
        "Nov 1 09:05 · Big.pdf · USB · Copied to Kindle",
    ]


def test_history_shows_times_in_local_time(ks, home, utc, capsys):
    write_history(home, entry("2026-11-05T00:30:00+01:00", "Dune.epub"))

    assert history_lines(ks, capsys) == ["Nov 4 23:30 · Dune.epub · Email · Sent to Amazon"]


def test_history_shows_only_the_last_20_sends_newest_first(ks, home, utc, capsys):
    write_history(home, *[entry(f"2026-10-{day:02d}T12:00:00+00:00", f"Book{day}.epub")
                          for day in range(1, 26)])

    lines = history_lines(ks, capsys)

    assert len(lines) == 20
    assert lines[0] == "Oct 25 12:00 · Book25.epub · Email · Sent to Amazon"
    assert lines[-1] == "Oct 6 12:00 · Book6.epub · Email · Sent to Amazon"


def test_history_skips_unreadable_lines(ks, home, utc, capsys):
    write_history(home, entry("2026-11-04T23:17:00+00:00", "Dune.epub"), {"name": "no time"})

    assert history_lines(ks, capsys) == ["Nov 4 23:17 · Dune.epub · Email · Sent to Amazon"]


def test_history_without_any_sends_says_so(ks, home, capsys):
    assert history_lines(ks, capsys) == ["No Sends yet."]
