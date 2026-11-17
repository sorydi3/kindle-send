"""Bar.js, run under node (skipped without node): what the bar widget shows (spec §17).

A book icon; beside it the count of Books waiting for the Kindle plus emails
held by the Send limit, only when non-zero; the bar's active colour while a
Send runs; tooltip "Books to Kindle" plus the state.
"""
import json

from qmljs import evaluate, needs_node

pytestmark = needs_node


def books(n):
    return [{"path": f"/b/{i}", "name": f"Book{i}.epub", "route": "usb"} for i in range(n)]


def status(waiting=0, held=0, busy=False, tr="EN"):
    service = {"pending": books(waiting), "held": books(held), "busy": busy}
    return evaluate("Bar.js", f"status({json.dumps(service)}, {tr})")


def test_nothing_waiting_shows_no_count():
    assert status() == {"label": "", "active": False,
                        "tooltip": "Books to Kindle\nNothing waiting"}


def test_books_waiting_for_the_kindle_are_counted():
    assert status(waiting=2) == {"label": "2", "active": False,
                                 "tooltip": "Books to Kindle\n2 waiting for Kindle"}


def test_emails_held_by_the_send_limit_are_counted():
    assert status(held=3) == {"label": "3", "active": False,
                              "tooltip": "Books to Kindle\n3 held by the Send limit"}


def test_waiting_and_held_add_up_and_both_show():
    assert status(waiting=1, held=4) == {
        "label": "5", "active": False,
        "tooltip": "Books to Kindle\n1 waiting for Kindle · 4 held by the Send limit"}


def test_a_send_running_turns_the_icon_active():
    assert status(busy=True) == {"label": "", "active": True,
                                 "tooltip": "Books to Kindle\nSending…"}


def test_sending_comes_first_beside_what_waits():
    assert status(waiting=1, busy=True) == {
        "label": "1", "active": True,
        "tooltip": "Books to Kindle\nSending… · 1 waiting for Kindle"}


def test_counts_are_plural_entries_with_formatted_numbers():
    """A language's own digits show in the label and the tooltip (here Arabic-Indic)."""
    got = status(waiting=1, held=2, tr="LANG({}, '\\u0660')")

    assert got["label"] == "٣"
    assert got["tooltip"] == "Books to Kindle\n١ waiting for Kindle · ٢ held by the Send limit"


def test_the_widget_text_comes_from_the_catalog():
    tr = "LANG({'bar.waiting': {one: '%1 wartet', other: '%1 warten'}, 'bar.idle': 'Nichts wartet'})"

    assert status(waiting=2, tr=tr)["tooltip"] == "Books to Kindle\n2 warten"
    assert status(waiting=1, tr=tr)["tooltip"] == "Books to Kindle\n1 wartet"
    assert status(tr=tr)["tooltip"] == "Books to Kindle\nNichts wartet"


def test_before_the_service_loads_nothing_waits():
    assert evaluate("Bar.js", "status(null, EN)") == {
        "label": "", "active": False, "tooltip": "Books to Kindle\nNothing waiting"}


QT_LEFT, QT_RIGHT, QT_MIDDLE = 0x1, 0x2, 0x4


def test_only_a_left_click_toggles_the_picker():
    assert evaluate("Bar.js", f"[togglesPicker({QT_LEFT}), togglesPicker({QT_RIGHT}),"
                              f" togglesPicker({QT_MIDDLE})]") == [True, False, False]
