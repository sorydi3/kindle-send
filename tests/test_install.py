"""scripts/install.sh, run against a temp HOME with stub omarchy commands.

The real `omarchy` and `omarchy-shell` live in /usr/bin, so PATH must not
include it: it holds only the stubs and links to a short list of basic tools.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
INSTALL = REPO / "scripts" / "install.sh"
PLUGIN_ID = "sorydi3.kindle-send"
BASIC_TOOLS = ["bash", "cat", "chmod", "cp", "dirname", "grep", "install", "ln", "mkdir",
               "readlink", "rm", "sleep"]


def basic_tools(directory):
    directory.mkdir()
    for tool in BASIC_TOOLS:
        real = shutil.which(tool, path="/usr/bin:/bin")
        assert real, tool
        (directory / tool).symlink_to(real)


def stub(directory, name, body):
    path = directory / name
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "stubs"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    rescanned = tmp_path / "rescanned"
    stub(bin_dir, "omarchy-shell", f'echo "omarchy-shell $*" >> "{log}"\n'
         f'[[ "$*" == *rescanPlugins* ]] && : > "{rescanned}"\nexit 0\n')
    # `plugin list` shows the plugin only once the shell has rescanned.
    stub(bin_dir, "omarchy", f'echo "omarchy $*" >> "{log}"\n'
         f'if [[ "$1 $2" == "plugin list" ]]; then\n'
         f'  [[ -f "{rescanned}" ]] && echo \'[{{"id":"{PLUGIN_ID}"}}]\' || echo "[]"\n'
         f'fi\nexit 0\n')
    tools = tmp_path / "tools"
    basic_tools(tools)
    environ = {
        "HOME": str(home),
        "PATH": f"{bin_dir}:{tools}",
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
    }
    return {"home": home, "env": environ, "log": log, "bin": bin_dir, "tools": tools}


def install(env, *args):
    return subprocess.run([str(env["tools"] / "bash"), str(INSTALL), *args], env=env["env"], cwd=env["home"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)


def calls(env):
    return env["log"].read_text().splitlines() if env["log"].exists() else []


def paths(env):
    home = env["home"]
    copy = home / ".local" / "share" / "kindle-send" / "omarchy-plugin"
    return {"bin": home / ".local" / "bin" / "kindle-send", "copy": copy,
            "link": home / ".config" / "omarchy" / "plugins" / PLUGIN_ID}


def test_install_copies_the_command_and_plugin_and_links_the_plugin(env):
    result = install(env)

    assert result.returncode == 0, result.stderr
    p = paths(env)
    assert p["bin"].read_bytes() == (REPO / "bin" / "kindle-send").read_bytes()
    assert os.access(p["bin"], os.X_OK)
    for name in ("manifest.json", "Picker.qml", "Service.qml"):
        assert (p["copy"] / name).read_bytes() == (REPO / "plugin" / name).read_bytes()
    assert p["link"].is_symlink()
    assert Path(os.readlink(p["link"])) == p["copy"]


def test_install_rescans_then_enables_the_plugin(env):
    install(env)

    log = calls(env)
    rescan = log.index("omarchy-shell -q shell rescanPlugins")
    enable = log.index(f"omarchy plugin enable {PLUGIN_ID}")
    assert rescan < enable


def test_rerunning_install_replaces_the_copy_and_keeps_the_link(env):
    install(env)
    p = paths(env)
    (p["copy"] / "Stale.qml").write_text("old")

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert not (p["copy"] / "Stale.qml").exists()
    assert (p["copy"] / "manifest.json").exists()
    assert Path(os.readlink(p["link"])) == p["copy"]


def test_something_else_at_the_plugin_link_is_left_alone(env):
    p = paths(env)
    p["link"].mkdir(parents=True)
    (p["link"] / "mine.txt").write_text("dev clone")

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert not p["link"].is_symlink()
    assert (p["link"] / "mine.txt").read_text() == "dev clone"
    assert "left alone" in result.stdout


def test_no_real_omarchy_command_is_reachable(env):
    found = subprocess.run([str(env["tools"] / "bash"), "-c", "type -P omarchy-plugin-enable omarchy-shell-config"],
                           env=env["env"], capture_output=True, text=True)
    assert found.stdout == ""


def test_without_omarchy_the_command_is_still_installed(env):
    (env["bin"] / "omarchy").unlink()

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert paths(env)["bin"].exists()
    assert not paths(env)["link"].exists()
