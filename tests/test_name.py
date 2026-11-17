"""The plugin is called "Books to Kindle" wherever it is shown (spec §17, Name, README and listing).

"Send to Kindle" is Amazon's product name; it survives only as the right-click action label,
which says what the item does.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The files that ship and show text, and the lines in them allowed to say "Send to Kindle":
# the Nautilus and Strata right-click action labels, and text pointing at them.
SHIPPED = ["manifest.json", "Picker.qml", "Service.qml", "BarWidget.qml", "Feedback.js", "Settings.js",
           "Rows.js", "Pending.js", "Limit.js", "Routes.js", "bin/kindle-send", "nautilus/kindle-send.py",
           "scripts/install.sh", "scripts/menu_block.py", "scripts/strata_action.py"]
RIGHT_CLICK = [
    'label="Send to Kindle"',                     # Nautilus menu item
    'name = "Send to Kindle"',                    # Strata action name
    'right-click "Send to Kindle"',               # docstrings naming that item
    "choose Send to Kindle",                      # install.sh: where to find the item
    "Actions → Send to Kindle",                   # strata_action.py: where to turn it on
]


def test_no_shown_text_says_send_to_kindle_except_the_right_click_action():
    offending = []
    for name in SHIPPED:
        path = REPO / name
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "Send to Kindle" in line and not any(allowed in line for allowed in RIGHT_CLICK):
                offending.append(f"{name}:{number}: {line.strip()}")

    assert offending == []


def test_the_manifest_carries_the_name_and_the_listing_fields():
    manifest = json.loads((REPO / "manifest.json").read_text())

    assert manifest["id"] == "sorydi3.kindle-send"
    assert manifest["name"] == "Books to Kindle"
    assert manifest["version"] == "1.0.0"
    assert manifest["author"] == "sorydi3"
    assert manifest["license"] == "MIT"
    assert manifest["description"] == ("Unofficial: send ebooks to your Kindle by email or USB. "
                                       "Not created or endorsed by Amazon.")
