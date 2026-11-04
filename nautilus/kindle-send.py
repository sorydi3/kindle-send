"""Nautilus right-click "Send to Kindle" (spec §4).

The item appears when at least one selected file has a supported format; folders
and non-local files never count. Activating it summons the Picker with those
files. Unsupported files in the selection are left out and named in a notification.

The supported formats are not listed here: they come from `kindle-send formats`,
asked once per Nautilus process. No `kindle-send` on PATH means no item.
"""
import json
import os
import shutil
import subprocess

from gi import require_version

require_version("Nautilus", "4.1")

from gi.repository import GObject, Gio, Nautilus  # noqa: E402

PLUGIN_ID = "sorydi3.kindle-send"
BOOK_GLYPH = ""

_formats = None


def supported_formats():
    """Lowercase extensions without the dot, from `kindle-send formats`; empty if unavailable."""
    global _formats
    if _formats is not None:
        return _formats
    command = shutil.which("kindle-send")
    if not command:
        return set()
    try:
        out = subprocess.run([command, "formats"], capture_output=True, text=True,
                             timeout=5, check=True).stdout
        _formats = set(json.loads(out.splitlines()[0])["formats"])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
        return set()
    return _formats


def split_selection(files, formats):
    """(supported paths, names of unsupported files), in selection order, without repeats."""
    books, skipped, seen = [], [], set()
    for file in files:
        if file.is_directory():
            continue
        location = file.get_location()
        path = location.get_path() if location else None
        if not path or path in seen:
            continue
        seen.add(path)
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in formats:
            books.append(path)
        else:
            skipped.append(os.path.basename(path))
    return books, skipped


def left_out_notification(names):
    one = len(names) == 1
    headline = f"Left out {len(names)} file{'' if one else 's'}"
    body = ", ".join(names) + (": Kindle can't take this format." if one
                               else ": Kindle can't take these formats.")
    return ["omarchy-notification-send", "--app-name", "Send to Kindle", "-g", BOOK_GLYPH,
            "-u", "normal", headline, body]


def summon_argv(books):
    return ["omarchy-shell", "shell", "summon", PLUGIN_ID, json.dumps({"files": books})]


class SendToKindle(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, *args):
        # Nautilus 4 passes (files); Nautilus 3 passed (window, files).
        files = args[0] if len(args) == 1 else args[1]
        books, skipped = split_selection(files, supported_formats())
        if not books:
            return []
        item = Nautilus.MenuItem(name="KindleSendNautilus::send", label="Send to Kindle",
                                 icon="mail-send")
        item.connect("activate", self._on_activate, books, skipped)
        return [item]

    def _on_activate(self, _item, books, skipped):
        # argv lists, never a shell: file names may hold spaces, quotes or non-ASCII.
        if skipped:
            Gio.Subprocess.new(left_out_notification(skipped), Gio.SubprocessFlags.NONE)
        Gio.Subprocess.new(summon_argv(books), Gio.SubprocessFlags.NONE)
