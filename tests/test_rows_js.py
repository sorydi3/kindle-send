"""plugin/Rows.js, run under node (skipped without node): the Picker's row text."""
import json

from qmljs import evaluate, needs_node

pytestmark = needs_node

NOW = "Date.parse('2026-11-05T12:00:00Z')"


def rows(expr):
    return evaluate("Rows.js", expr)


def book(**fields):
    base = {"name": "Dune.epub", "format": "epub", "size": 1_200_000, "route": "email",
            "routeReason": "", "emailOk": True, "usbOk": True, "lastSent": None}
    return json.dumps({**base, **fields})


def test_a_book_sent_three_days_ago_says_so():
    text = rows(f"details({book(lastSent='2026-11-02T11:00:00+00:00')}, 'email', {NOW})")

    assert text == "EPUB · 1.2 MB · sent 3 days ago"


def test_a_book_sent_yesterday():
    assert rows(f"details({book(lastSent='2026-11-04T09:00:00+00:00')}, 'email', {NOW})") \
        == "EPUB · 1.2 MB · sent yesterday"


def test_a_book_never_sent_has_no_mark():
    assert rows(f"details({book()}, 'email', {NOW})") == "EPUB · 1.2 MB"


def test_an_already_sent_book_is_sent_again_like_any_other():
    """Re-sending needs no confirmation: marking a sent Book sends it."""
    chosen = rows(f"toSend([{book(path='/b/Dune.epub', lastSent='2026-11-02T11:00:00+00:00')}],"
                  " {'/b/Dune.epub': true}, {}, 0)")

    assert chosen == [{"path": "/b/Dune.epub", "name": "Dune.epub", "route": "email"}]


def test_enter_on_the_waiting_line_sends_nothing():
    waiting = json.dumps({"waiting": True, "path": "", "name": "1 Book waiting for Kindle"})

    assert rows(f"toSend([{book(path='/b/Dune.epub')}], {{}}, {{}}, {waiting})") == []


def test_a_plan_that_needs_setup_switches_the_picker_to_setup():
    """The Picker then shows only "Set up Send to Kindle" (spec §4, §9)."""
    parsed = rows("fromPlan([{setupNeeded: true, missing: ['appPassword']},"
                  f" {book(path='/b/Dune.epub')}])")

    assert parsed["setupNeeded"] is True


def test_a_plan_without_setup_needed_lists_books():
    parsed = rows(f"fromPlan([{book(path='/b/Dune.epub')}])")

    assert parsed["setupNeeded"] is False
    assert [b["path"] for b in parsed["books"]] == ["/b/Dune.epub"]
