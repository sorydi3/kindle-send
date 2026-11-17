#!/usr/bin/env python3
"""Write Strata's right-click "Send to Kindle" action (spec §4).

    strata_action.py ACTIONS_DIR FORMATS_JSON

FORMATS_JSON is the output of `kindle-send formats`, so the format list lives
only in kindle-send. Writes ACTIONS_DIR/kindle-send/action.toml, owner-only as
Strata requires. A new action starts disabled, for the user to enable in
Strata's Settings → Actions; a rerun keeps the user's choice.

Strata shows an action only when every selected file matches it, so a mixed
selection gets no item (Nautilus instead leaves the unsupported files out).
"""
import json
import os
import re
import sys

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


def main(actions_dir, formats_json):
    try:
        formats = json.loads(formats_json.splitlines()[0])["formats"]
    except (ValueError, KeyError, IndexError, TypeError):
        sys.exit("    Couldn't read the formats from kindle-send; Strata action not added.")

    folder = os.path.join(actions_dir, ACTION_ID)
    path = os.path.join(folder, "action.toml")
    enabled = "false"
    try:
        with open(path, encoding="utf-8") as f:
            found = re.search(r"^enabled = (true|false)$", f.read(), re.M)
        if found:
            enabled = found.group(1)
        existed = True
    except FileNotFoundError:
        existed = False

    os.makedirs(folder, mode=0o700, exist_ok=True)
    os.chmod(folder, 0o700)
    text = TEMPLATE.format(id=ACTION_ID, enabled=enabled, extensions=json.dumps(formats))
    tmp = path + ".kindle-send-tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

    if not existed:
        print(f"    Added {path}, turned off.")
        print("    Turn it on in Strata: Settings → Actions → Send to Kindle.")
    elif enabled == "true":
        print(f"    Updated {path}.")
    else:
        print(f"    Updated {path}; still off. Turn it on in Strata: Settings → Actions.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
