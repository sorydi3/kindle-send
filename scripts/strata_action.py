#!/usr/bin/env python3
"""Write Strata's right-click "Send to Kindle" action (spec §4).

    strata_action.py ACTIONS_DIR FORMATS_JSON
    strata_action.py --current ACTIONS_DIR FORMATS_JSON

FORMATS_JSON is the output of `kindle-send formats`, so the format list lives
only in kindle-send. Writes ACTIONS_DIR/kindle-send/action.toml, owner-only as
Strata requires. A new action starts disabled, for the user to enable in
Strata's Settings → Actions; a rerun keeps the user's choice. With --current it
writes nothing and exits 0 if the action is already what it would write, 3 if not.

Strata shows an action only when every selected file matches it, so a mixed
selection gets no item (Nautilus instead leaves the unsupported files out).
"""
import json
import os
import re
import sys
import tempfile

ACTION_ID = "kindle-send"

TEMPLATE = """\
# Added by kindle-send's scripts/install.sh; rewritten on each install.
schema_version = 1
id = "{id}"
name = "Send to Kindle"
description = "Open the Books to Kindle picker with these books"
icon = "send-horizontal"
enabled = {enabled}
menu = "top"

[when]
kinds = ["file"]
extensions = {extensions}
min_items = 1

[run]
runtime = "command"
program = "kindle-send"
args = ["pick", "{{paths}}"]
mode = "whole-selection"
working_directory = "parent"
confirm = false
"""


def main(actions_dir, formats_json, only_check=False):
    try:
        formats = json.loads(formats_json.splitlines()[0])["formats"]
    except (ValueError, KeyError, IndexError, TypeError):
        sys.exit("    Couldn't read the formats from kindle-send; Strata action not added.")

    folder = os.path.join(actions_dir, ACTION_ID)
    path = os.path.join(folder, "action.toml")
    enabled = "false"
    try:
        with open(path, encoding="utf-8") as f:
            old = f.read()
        found = re.search(r"^enabled = (true|false)$", old, re.M)
        if found:
            enabled = found.group(1)
        existed = True
    except FileNotFoundError:
        old, existed = None, False

    text = TEMPLATE.format(id=ACTION_ID, enabled=enabled, extensions=json.dumps(formats))
    if only_check:
        return 0 if text == old else 3

    if os.path.islink(folder):
        sys.exit(f"    {folder} is a link; the Strata action was not written.")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    os.chmod(folder, 0o700, follow_symlinks=False)
    # A fresh owner-only staging file (never a fixed path a planted link could
    # redirect), renamed over the action, which replaces a link instead of following it.
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".action.toml.", suffix=".kindle-send-tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise

    if not existed:
        print(f"    Added {path}, turned off.")
        print("    Turn it on in Strata: Settings → Actions → Send to Kindle.")
    elif enabled == "true":
        print(f"    Updated {path}.")
    else:
        print(f"    Updated {path}; still off. Turn it on in Strata: Settings → Actions.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    check = args[:1] == ["--current"]
    if check:
        args = args[1:]
    if len(args) != 2:
        sys.exit(__doc__)
    sys.exit(main(*args, only_check=check))
