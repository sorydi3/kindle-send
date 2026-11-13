"""scripts/uninstall.sh, run against a temp HOME after scripts/install.sh, with stub commands."""
import json
import os
import subprocess

from test_install import (BINDINGS_TEXT, MENU_TEXT, MENU_WITH_OLD_BLOCK, PLUGIN_ID, REPO, calls, config_files, env, install,  # noqa: F401
                          paths, run_tty, shell_parse, stub)

UNINSTALL = REPO / "scripts" / "uninstall.sh"


def uninstall(env, *args):
    return subprocess.run([str(env["tools"] / "bash"), str(UNINSTALL), *args], env=env["env"], cwd=env["home"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)


def user_data(env):
    """Settings, a stored password and a Send history, as setup and sends leave them."""
    home = env["home"]
    shell = home / ".config" / "omarchy" / "shell.json"
    shell.parent.mkdir(parents=True, exist_ok=True)
    shell.write_text(json.dumps({"bar": {"id": "omarchy.bar"}, "plugins": [
        {"id": "other.plugin"},
        {"id": PLUGIN_ID, "kindleAddress": "reader@kindle.com", "senderAddress": "sender@gmail.com"}]}))
    history = home / ".local" / "state" / "kindle-send" / "history.jsonl"
    history.parent.mkdir(parents=True)
    history.write_text('{"name":"Dune.epub"}\n')
    return shell, history


def installed(env):
    config_files(env)
    result = install(env, "--yes")
    assert result.returncode == 0, result.stderr
    return user_data(env)


def test_uninstall_removes_the_files_and_the_plugin_link(env):
    installed(env)

    result = uninstall(env)

    assert result.returncode == 0, result.stderr
    p = paths(env)
    data = env["home"] / ".local" / "share"
    assert not p["bin"].exists() and not p["bin"].is_symlink()
    assert not p["link"].exists() and not p["link"].is_symlink()
    assert not (data / "kindle-send").exists()
    assert not (data / "nautilus-python" / "extensions" / "kindle-send.py").exists()


def test_uninstall_tells_the_shell_and_nautilus(env):
    installed(env)
    before = len(calls(env))

    uninstall(env)

    log = calls(env)[before:]
    assert "omarchy-shell -q shell rescanPlugins" in log
    assert "nautilus -q" in log
    # `omarchy plugin remove` disables the plugin, which drops its settings from shell.json.
    assert not any(line.startswith("omarchy plugin remove") for line in log)


def test_uninstall_removes_the_marker_blocks_and_leaves_the_rest(env):
    installed(env)
    b, m = config_files(env, bindings=None, menu=None)

    result = uninstall(env)

    assert result.returncode == 0, result.stderr
    assert b.read_text() == BINDINGS_TEXT
    assert "kindle-send" not in m.read_text()
    assert shell_parse(m.read_text()) == shell_parse(MENU_TEXT)


def test_uninstall_removes_the_settings_entry_and_an_older_installs_setup_entry(env):
    installed(env)
    _, m = config_files(env, bindings=None, menu=None)
    assert "kindle-send.settings" in shell_parse(m.read_text())
    uninstall(env)
    assert "kindle-send" not in m.read_text()

    _, m = config_files(env, bindings=None, menu=MENU_WITH_OLD_BLOCK)
    result = uninstall(env)

    assert result.returncode == 0, result.stderr
    assert "kindle-send" not in m.read_text()
    assert shell_parse(m.read_text()) == shell_parse(MENU_TEXT)


def test_uninstall_keeps_settings_password_and_history(env):
    shell, history = installed(env)
    settings = shell.read_text()

    result = uninstall(env)

    assert shell.read_text() == settings
    assert history.exists()
    assert not any(line.startswith("secret-tool") for line in calls(env))
    assert "--purge" in result.stdout


def test_purge_also_removes_settings_password_and_history(env):
    shell, history = installed(env)

    result = uninstall(env, "--purge")

    assert result.returncode == 0, result.stderr
    config = json.loads(shell.read_text())
    assert config == {"bar": {"id": "omarchy.bar"}, "plugins": [{"id": "other.plugin"}]}
    assert not history.parent.exists()
    assert "secret-tool clear service kindle-send" in calls(env)


def test_something_else_at_the_plugin_link_is_left_alone(env):
    p = paths(env)
    p["link"].mkdir(parents=True)

    result = uninstall(env)

    assert result.returncode == 0, result.stderr
    assert p["link"].is_dir()
    assert "left alone" in result.stdout


def test_a_kindle_send_command_that_is_not_ours_is_left_alone(env):
    p = paths(env)
    p["bin"].parent.mkdir(parents=True)
    p["bin"].write_text("#!/bin/sh\necho someone else's\n")

    uninstall(env)

    assert p["bin"].exists()


def test_uninstall_on_a_clean_home_succeeds(env):
    result = uninstall(env)

    assert result.returncode == 0, result.stderr


def test_install_after_uninstall_adds_the_blocks_again_once(env):
    installed(env)
    uninstall(env)

    install(env, "--yes")

    b, m = config_files(env, bindings=None, menu=None)
    assert b.read_text().count("kindle-send keybinding") == 1
    assert m.read_text().count("kindle-send menu") == 1
    assert "kindle-send.pick" in shell_parse(m.read_text())


def test_uninstall_removes_the_strata_action(env):
    stub(env["bin"], "strata", "exit 0\n")
    installed(env)
    action = env["home"] / ".config" / "strata" / "actions" / "kindle-send"
    assert action.exists()

    result = uninstall(env)

    assert result.returncode == 0, result.stderr
    assert not action.exists()
    assert action.parent.exists()
