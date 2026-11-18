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


def test_a_link_planted_at_the_old_staging_path_is_not_written_through(tmp_path):
    actions = tmp_path / "actions"
    (actions / "kindle-send").mkdir(parents=True)
    victim = tmp_path / "victim"
    victim.write_text("someone's file\n")
    (actions / "kindle-send" / "action.toml.kindle-send-tmp").symlink_to(victim)

    out = write(actions)

    assert out.returncode == 0, out.stderr
    assert victim.read_text() == "someone's file\n"
    assert manifest(actions)["id"] == "kindle-send"
    assert stat.S_IMODE((actions / "kindle-send" / "action.toml").stat().st_mode) == 0o600


def test_a_link_at_the_action_file_is_replaced_not_written_through(tmp_path):
    actions = tmp_path / "actions"
    (actions / "kindle-send").mkdir(parents=True)
    victim = tmp_path / "victim.toml"
    victim.write_text("enabled = true\n")
    path = actions / "kindle-send" / "action.toml"
    path.symlink_to(victim)

    out = write(actions)

    assert out.returncode == 0, out.stderr
    assert victim.read_text() == "enabled = true\n"
    assert not path.is_symlink()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_an_action_folder_that_is_a_link_is_refused(tmp_path):
    actions = tmp_path / "actions"
    actions.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(mode=0o755)
    (actions / "kindle-send").symlink_to(elsewhere)

    out = write(actions)

    assert out.returncode != 0
    assert list(elsewhere.iterdir()) == []
    assert stat.S_IMODE(elsewhere.stat().st_mode) == 0o755


def test_no_staging_file_is_left_beside_the_action(tmp_path):
    actions = tmp_path / "actions"

    write(actions)
    write(actions, FORMATS + ["mobi"])

    assert [f.name for f in (actions / "kindle-send").iterdir()] == ["action.toml"]


def test_bad_formats_input_fails_without_writing(tmp_path):
    actions = tmp_path / "actions"

    out = subprocess.run([sys.executable, "-I", str(HELPER), str(actions), "not json"],
                         capture_output=True, text=True, timeout=10)

    assert out.returncode != 0
    assert not (actions / "kindle-send").exists()


def current(actions, formats=FORMATS):
    return subprocess.run([sys.executable, "-I", str(HELPER), "--current", str(actions),
                           json.dumps({"formats": formats})], capture_output=True, text=True, timeout=10)


def test_current_says_whether_the_action_is_up_to_date_without_writing(tmp_path):
    actions = tmp_path / "actions"
    assert current(actions).returncode == 3
    assert not (actions / "kindle-send").exists()

    write(actions)
    path = actions / "kindle-send" / "action.toml"
    path.write_text(path.read_text().replace("enabled = false", "enabled = true"))
    before = path.read_text()

    assert current(actions).returncode == 0  # the user's on/off choice is theirs
    assert current(actions, FORMATS + ["mobi"]).returncode == 3
    assert path.read_text() == before
