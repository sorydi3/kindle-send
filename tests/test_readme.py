"""The repo is ready to list (spec §17): a root README and an MIT LICENSE.

`omarchy plugin validate` on the root is checked in test_layout.py.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"


def sections():
    return re.findall(r"^## (.+)$", README.read_text(), re.M)


def test_the_readme_opens_with_the_name_and_the_not_affiliated_line():
    text = README.read_text()
    manifest = json.loads((REPO / "manifest.json").read_text())

    assert text.splitlines()[0] == "# Books to Kindle"
    assert manifest["description"] in text
    assert "](preview.png)" in text


def test_the_readme_has_the_listing_sections_in_order():
    wanted = ["Requires", "Install", "Configure", "Use", "Update", "Remove", "Security"]

    assert [s for s in sections() if s in wanted] == wanted


def test_the_readme_gives_the_shipped_commands():
    text = README.read_text()

    assert "omarchy plugin add https://github.com/sorydi3/kindle-send --enable" in text
    assert "~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh" in text
    assert "install.sh --remove" in text
    assert "--purge" in text
    assert "omarchy plugin update sorydi3.kindle-send" in text
    assert "omarchy plugin remove sorydi3.kindle-send" in text
    assert "secret-tool clear service kindle-send" in text
    assert "~/.config/kindle-send" in text and "~/.local/state/kindle-send" in text


def test_the_readme_mentions_no_real_address():
    # Only the services' own hosts may appear; no one's email address.
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", README.read_text())

    assert emails == []


def test_the_license_is_mit_for_sorydi3():
    text = (REPO / "LICENSE").read_text()

    assert text.startswith("MIT License")
    assert "Copyright (c) 2026 sorydi3" in text
    assert "THE SOFTWARE IS PROVIDED \"AS IS\"" in text
