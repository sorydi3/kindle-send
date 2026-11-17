"""The repo root is the plugin (spec §2, §17): Omarchy installs the repo as it is."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_the_manifest_and_its_entry_points_are_at_the_repo_root():
    manifest = json.loads((REPO / "manifest.json").read_text())

    assert manifest["id"] == "sorydi3.kindle-send"
    for entry in manifest["entryPoints"].values():
        assert (REPO / entry).is_file(), entry
    assert not (REPO / "plugin").exists()


@pytest.mark.skipif(shutil.which("git") is None or not (REPO / ".git").exists(), reason="not a git checkout")
def test_the_repo_tracks_no_symlinks():
    # What `omarchy plugin add` clones is what git tracks; its validator forbids symlinks inside.
    tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "-s"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    links = [line.split("\t", 1)[1] for line in tracked if line.startswith("120000 ")]

    assert links == []


@pytest.mark.skipif(shutil.which("omarchy") is None, reason="omarchy is not installed")
def test_omarchy_validates_the_repo_root_as_a_plugin():
    result = subprocess.run(["omarchy", "plugin", "validate", str(REPO)], capture_output=True, text=True,
                            timeout=60)

    assert result.returncode == 0, result.stdout + result.stderr
