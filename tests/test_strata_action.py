"""scripts/strata_action.py: Strata's right-click "Send to Kindle" action (spec §4)."""
import json
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "strata_action.py"
FORMATS = ["epub", "pdf", "txt"]


def write(actions, formats=FORMATS):
    return subprocess.run([sys.executable, "-I", str(HELPER), str(actions), json.dumps({"formats": formats})],
                          capture_output=True, text=True, timeout=10)


def manifest(actions):
    return tomllib.loads((actions / "kindle-send" / "action.toml").read_text())


def test_writes_a_disabled_top_level_action_for_the_supported_formats(tmp_path):
    actions = tmp_path / "strata" / "actions"

    out = write(actions)

    assert out.returncode == 0, out.stderr
    action = manifest(actions)
    assert action["id"] == "kindle-send"
    assert action["name"] == "Send to Kindle"
    assert action["enabled"] is False
    assert action["menu"] == "top"
    assert action["when"] == {"kinds": ["file"], "extensions": FORMATS, "min_items": 1}
    assert action["run"]["runtime"] == "command"
    assert action["run"]["program"] == "kindle-send"
    assert action["run"]["args"] == ["pick", "{paths}"]
    assert action["run"]["mode"] == "whole-selection"
    assert "Settings" in out.stdout


def test_files_are_owner_only_as_strata_requires(tmp_path):
    actions = tmp_path / "actions"

    write(actions)

    assert stat.S_IMODE((actions / "kindle-send").stat().st_mode) == 0o700
    assert stat.S_IMODE((actions / "kindle-send" / "action.toml").stat().st_mode) == 0o600


def test_rerun_keeps_the_users_enabled_choice_and_updates_the_formats(tmp_path):
    actions = tmp_path / "actions"
    write(actions)
    path = actions / "kindle-send" / "action.toml"
    path.write_text(path.read_text().replace("enabled = false", "enabled = true"))

    write(actions, FORMATS + ["mobi"])

    action = manifest(actions)
    assert action["enabled"] is True
    assert action["when"]["extensions"] == FORMATS + ["mobi"]


def test_bad_formats_input_fails_without_writing(tmp_path):
    actions = tmp_path / "actions"

    out = subprocess.run([sys.executable, "-I", str(HELPER), str(actions), "not json"],
                         capture_output=True, text=True, timeout=10)

    assert out.returncode != 0
    assert not (actions / "kindle-send").exists()
