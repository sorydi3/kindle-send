#!/usr/bin/env python3
"""Add, remove or check the kindle-send block in omarchy-menu.jsonc.

    menu_block.py add FILE     insert the block before the final "}" (creates FILE if missing)
    menu_block.py remove FILE  delete the block's lines
    menu_block.py current FILE exit 0 if FILE's block is this version's
    menu_block.py update FILE  swap an older install's block for this one, in place
    menu_block.py check FILE   exit 0 if the shell can parse FILE

Exit codes: 0 done (current: yes), 1 FILE does not parse (left alone), 3 add: block
already there, remove/update: no block, current: no. "Parses" means by the shell's own rules (MenuModel.js stripJsonc):
only whole-line // comments and trailing commas are allowed.
"""
import json
import os
import re
import sys

START = "// >>> kindle-send menu (added by scripts/install.sh) >>>"
END = "// <<< kindle-send <<<"
PICK = "omarchy-shell shell toggle sorydi3.kindle-send"
# Opens the Picker in Settings, on no field in particular (spec §14).
SETTINGS = "omarchy-shell shell summon sorydi3.kindle-send '{\"settings\":\"\"}'"
ENTRIES = [
    ("kindle-send", {"icon": "\U000F00BA", "label": "Books to Kindle", "aliases": ["kindle"]}),
    ("kindle-send.pick", {"icon": "\U000F00BA", "label": "Books to Kindle", "action": PICK}),
    ("kindle-send.settings", {"icon": "", "label": "Settings", "action": SETTINGS}),
]


def parses(text):
    stripped = re.sub(r"^\s*//[^\n]*(\n|$)", "", text, flags=re.M)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    try:
        return isinstance(json.loads(stripped), dict)
    except ValueError:
        return False


def block():
    lines = [START]
    for key, value in ENTRIES:
        lines.append(f"{json.dumps(key)}: {json.dumps(value, ensure_ascii=False, separators=(',', ':'))},")
    lines.append(END)
    return "\n".join("  " + line for line in lines)


def is_code(line):
    stripped = line.strip()
    return stripped and not stripped.startswith("//")


def add(text):
    """The text with the block inserted before its final "}"."""
    close = text.rindex("}")
    lines = text[:close].rstrip().split("\n")
    last = max(i for i, line in enumerate(lines) if is_code(line))
    if not lines[last].rstrip().endswith((",", "{")):
        lines[last] = lines[last].rstrip() + ","
    return "\n".join(lines) + "\n" + block() + "\n" + text[close:]


def swap_block(text, lines):
    """The text with `lines` in place of the block's lines."""
    out, inside = [], False
    for line in text.split("\n"):
        if line.strip() == START:
            inside = True
            out.extend(lines)
        elif inside:
            inside = line.strip() != END
        else:
            out.append(line)
    return "\n".join(out)


def remove(text):
    """The text without the block's lines."""
    return swap_block(text, [])


def replace(text, replacement):
    """The text with `replacement` where the block's lines were."""
    return swap_block(text, [replacement])


def current(text):
    return block() in text


def write(path, text):
    tmp = f"{path}.kindle-send-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def main(argv):
    command, path = argv
    exists = os.path.exists(path)
    text = open(path, encoding="utf-8").read() if exists else ""
    if command == "check":
        return 0 if parses(text) else 1
    if command == "add":
        if START in text:
            return 3
        if not exists or not text.strip():
            write(path, "{\n" + block() + "\n}\n")
            return 0
        if not parses(text):
            return 1
        write(path, add(text))
        return 0
    if command == "remove":
        if START not in text:
            return 3
        write(path, remove(text))
        return 0
    if command == "current":
        return 0 if current(text) else 3
    if command == "update":
        if START not in text:
            return 3
        if not parses(text):
            return 1
        write(path, replace(text, block()))
        return 0
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
