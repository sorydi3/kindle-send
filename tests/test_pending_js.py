"""plugin/Pending.js: Pending Sends (spec §7, §10), run under node (skipped without node)."""
import json

import pytest

from qmljs import evaluate, needs_node

pytestmark = needs_node


def js(expr):
    return evaluate("Pending.js", expr)


def j(value):
    return json.dumps(value)


ATLAS = {"path": "/b/Atlas.pdf", "name": "Atlas.pdf", "route": "usb"}
DUNE = {"path": "/b/Dune.epub", "name": "Dune.epub", "route": "usb"}
NO_KINDLE = {"name": "Atlas.pdf", "result": "failed",
             "reason": "Kindle not plugged in. Plug it in and send again."}


def test_a_usb_book_failing_for_no_kindle_becomes_pending():
    assert js(f"isPending({j(ATLAS)}, {j(NO_KINDLE)})") is True


@pytest.mark.parametrize("book, result", [
    (ATLAS, {"name": "Atlas.pdf", "result": "copied"}),
    (ATLAS, {"name": "Atlas.pdf", "result": "failed", "reason": "Not enough space on the Kindle."}),
    ({**ATLAS, "route": "email"}, NO_KINDLE),
])
def test_other_results_are_not_pending(book, result):
    assert js(f"isPending({j(book)}, {j(result)})") is False


@pytest.mark.parametrize("text, found", [
    ('{"present": true, "mount": "/run/media/u/Kindle", "free": 100}\n', True),
    ('{"present": false}\n', False),
    ("", False),
    ("Traceback (most recent call last):\n", False),
])
def test_kindle_poll_reads_kindle_send_kindle(text, found):
    assert js(f"kindleFound({j(text)})") is found


def test_one_waiting_book_gets_a_lasting_notice_that_opens_the_picker():
    assert js(f"notice([{j(ATLAS)}])") == {
        "headline": "Waiting for Kindle: Atlas.pdf",
        "body": "Plug it in to send. Click to manage.",
        "urgency": "critical"}


def test_several_waiting_books_are_counted_and_named():
    n = js(f"notice([{j(ATLAS)}, {j(DUNE)}])")

    assert n["headline"] == "Waiting for Kindle: 2 Books"
    assert n["body"] == "Atlas.pdf, Dune.epub\nPlug it in to send. Click to manage."
    assert n["urgency"] == "critical"


def test_cancelling_replaces_the_lasting_notice_with_a_passing_one():
    assert js(f"cancelledNotice([{j(ATLAS)}, {j(DUNE)}])") == {
        "headline": "Cancelled 2 Books waiting for Kindle", "body": "", "urgency": "normal"}


def test_adding_the_same_book_again_keeps_one_pending_send():
    again = {**ATLAS, "name": "Atlas.pdf"}

    assert js(f"add([{j(ATLAS)}], [{j(again)}, {j(DUNE)}])") == [ATLAS, DUNE]


def test_the_waiting_line_goes_above_the_books_only_while_something_waits():
    rows = [{"path": "/b/Other.pdf", "name": "Other.pdf"}]

    assert js(f"withWaiting({j(rows)}, [])") == rows
    listed = js(f"withWaiting({j(rows)}, [{j(ATLAS)}, {j(DUNE)}])")
    assert listed[1:] == rows
    assert listed[0]["waiting"] is True
    assert listed[0]["name"] == "2 Books waiting for Kindle"
    assert listed[0]["details"] == "Atlas.pdf, Dune.epub"
    assert js(f"withWaiting([], [{j(ATLAS)}])")[0]["name"] == "1 Book waiting for Kindle"


@pytest.mark.parametrize("pending_key, results, wanted", [
    (0, 0, 7),    # the whole Send is waiting: its own notification turns into the notice
    (0, 1, 0),    # the Send has a summary of its own: the notice needs a new one
    (3, 0, 3),    # a notice is already up: update it
    (3, 2, 3),
])
def test_which_notification_carries_the_notice(pending_key, results, wanted):
    assert js(f"noticeKey({pending_key}, 7, {results})") == wanted
