"""Picker payload mode (spec §4): plugin/Rows.js run under node.

The Nautilus extension summons the Picker with {"files": [...]}; the Picker then
plans just those files and marks them all.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROWS = Path(__file__).resolve().parent.parent / "plugin" / "Rows.js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")


def rows(call):
    """Evaluate `call` (a JS expression using Rows.js functions) and return its JSON value."""
    source = ROWS.read_text().replace(".pragma library", "")
    script = source + f"\nprocess.stdout.write(JSON.stringify({call}))\n"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


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
