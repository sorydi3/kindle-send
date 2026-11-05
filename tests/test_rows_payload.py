"""Picker payload mode (spec §4): plugin/Rows.js run under node.

The Nautilus extension summons the Picker with {"files": [...]}; the Picker then
plans just those files and marks them all.
"""
import json

from qmljs import evaluate, needs_node

pytestmark = needs_node


def rows(call):
    """Evaluate `call` (a JS expression using Rows.js functions) and return its JSON value."""
    return evaluate("Rows.js", call)


def test_a_bind_opens_the_picker_on_the_book_folders():
    assert rows('planCommand(payloadFiles("{}"))') == ["kindle-send", "plan", "--folders"]
    assert rows('planCommand(payloadFiles(""))') == ["kindle-send", "plan", "--folders"]
    assert rows('planCommand(payloadFiles("not json"))') == ["kindle-send", "plan", "--folders"]


def test_a_files_payload_plans_just_those_files():
    payload = json.dumps({"files": ["/books/My Book é.epub", "/books/b.pdf"]})

    assert rows(f"planCommand(payloadFiles({json.dumps(payload)}))") == [
        "kindle-send", "plan", "/books/My Book é.epub", "/books/b.pdf"]


def test_non_string_entries_in_the_payload_are_ignored():
    assert rows('payloadFiles(\'{"files": ["/a.epub", 3, null, ""]}\')') == ["/a.epub"]


def test_every_planned_book_starts_marked():
    assert rows('allMarked([{path: "/a.epub"}, {path: "/b.pdf"}])') == {"/a.epub": True, "/b.pdf": True}
