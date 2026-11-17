"""The repo root is the plugin (spec §2, §17): Omarchy installs the repo as it is."""
import json
import os
import re
import shutil
import subprocess
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
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


def test_kindle_send_is_bundled_as_an_executable_beside_its_test_epub():
    assert os.access(REPO / "bin" / "kindle-send", os.X_OK)
    assert (REPO / "assets" / "test.epub").is_file()


def test_the_bundled_program_finds_the_test_epub_through_a_symlinked_plugin_folder(tmp_path, monkeypatch):
    # The author's setup: the plugin folder is a symlink to the checkout (spec §17).
    plugin = tmp_path / "plugins" / "sorydi3.kindle-send"
    plugin.parent.mkdir()
    plugin.symlink_to(REPO, target_is_directory=True)
    monkeypatch.delenv("KINDLE_SEND_TEST_EPUB", raising=False)
    loader = SourceFileLoader("kindle_send_linked", str(plugin / "bin" / "kindle-send"))
    ks = module_from_spec(spec_from_loader("kindle_send_linked", loader))
    loader.exec_module(ks)

    assert ks.test_epub_path().read_bytes() == (REPO / "assets" / "test.epub").read_bytes()


def test_no_plugin_file_runs_a_kindle_send_from_path():
    # The Picker can't run outside the shell, so its commands are checked here;
    # the Service's runs are checked under the fake Quickshell.Io (test_service_flow.py).
    bare = re.compile(r"""\[\s*["']kindle-send["']""")
    for f in [*REPO.glob("*.qml"), *REPO.glob("*.js")]:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            assert not bare.search(line), f"{f.name}:{n} runs a bare kindle-send: {line.strip()}"


@pytest.mark.skipif(shutil.which("omarchy") is None, reason="omarchy is not installed")
def test_omarchy_validates_the_repo_root_as_a_plugin():
    result = subprocess.run(["omarchy", "plugin", "validate", str(REPO)], capture_output=True, text=True,
                            timeout=60)

    assert result.returncode == 0, result.stdout + result.stderr
