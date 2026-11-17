"""The plugin's text lives in its English catalog, i18n/en.json (spec §17, Translations),
and every QML Text shows plain text (Omarchy's plugin UI safety rule).

Static checks over the shipped QML and JS; the text functions themselves are
tested under node (tests/test_catalog_js.py and the other *_js tests).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QML = sorted(ROOT.glob("*.qml"))
JS = sorted(ROOT.glob("*.js"))

# String literals that look like English but are not the plugin's text:
# key names stay as they are, the test Book's name is the title it shows on the Kindle,
# and catalog key prefixes (settings.) are keys.
NOT_TEXT = {"Esc", "Space", "Tab", "Enter", "Delete", "Ctrl+,", "Ctrl+O", "Ctrl+B", "Kindle Send Test",
            # A command, not text
            "omarchy-shell shell toggle sorydi3.kindle-send"}


def literals(source):
    """(line, text) of every string literal outside comments and import lines."""
    found, i, line = [], 0, 1
    while i < len(source):
        c = source[i]
        if c == "\n":
            line += 1
        if source.startswith("//", i):
            i = source.find("\n", i)
            i = len(source) if i < 0 else i
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i) + 2
            line += source.count("\n", i, end)
            i = end
            continue
        if c in "\"'`":
            j = i + 1
            while source[j] != c:
                j += 2 if source[j] == "\\" else 1
            start = source.rfind("\n", 0, i) + 1
            if not re.match(r"\s*\.?import\b", source[start:i]):
                found.append((line, source[i + 1:j]))
            line += source.count("\n", i, j)
            i = j + 1
            continue
        i += 1
    return found


def looks_english(text):
    if text in NOT_TEXT or re.fullmatch(r"[a-z][\w.]*", text):
        return False
    words = re.findall(r"[A-Za-z]{2,}", text)
    if not words:
        return False
    return (" " in text.strip()) or bool(re.match(r"[A-Z][a-z]+\b", text)) or bool(re.search(r"[A-Za-z][.…!?]$", text))


def test_no_english_is_hard_coded_in_the_plugins_qml_or_js():
    offending = [f"{path.name}:{line}: {text!r}"
                 for path in QML + JS for line, text in literals(path.read_text(encoding="utf-8"))
                 if looks_english(text)]

    assert offending == []


def test_the_check_would_catch_english():
    assert looks_english("Sent to Amazon.")
    assert looks_english("Settings")
    assert looks_english("Browse…")
    assert not looks_english("omarchy-notification-send")
    assert not looks_english("settings.title")
    assert not looks_english("Esc")


def text_blocks(source):
    """The body of every `Text { … }` element (not TextField and the like)."""
    for match in re.finditer(r"(?<![\w.])Text\s*\{", source):
        depth, i = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(source[i], 0)
            i += 1
        yield source.count("\n", 0, match.start()) + 1, source[match.end():i - 1]


def test_every_text_in_the_plugin_shows_plain_text():
    """Markup-shaped Book names or system text must never render as rich text (plugins.md, Plugin UI Safety)."""
    missing = [f"{path.name}:{line}" for path in QML for line, body in text_blocks(path.read_text())
               if "textFormat: Text.PlainText" not in body]

    assert missing == []


def test_the_picker_has_texts_to_check():
    assert len(list(text_blocks((ROOT / "Picker.qml").read_text()))) >= 10


def test_the_catalog_is_valid_flat_json():
    catalog = json.loads((ROOT / "i18n" / "en.json").read_text())

    assert isinstance(catalog, dict) and catalog


def test_every_key_the_plugin_reads_is_in_the_catalog():
    """A missing key would show as the key itself."""
    catalog = json.loads((ROOT / "i18n" / "en.json").read_text())
    read = set()
    for path in QML + JS:
        source = path.read_text(encoding="utf-8")
        read |= set(re.findall(r"""\b(?:t|tn|say|count)\((?:tr, )?["']([a-z]+\.[A-Za-z.]+)["']""", source))

    assert read and sorted(read - set(catalog)) == []
