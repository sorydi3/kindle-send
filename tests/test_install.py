"""scripts/install.sh, the optional extras script (spec §14), run against a temp HOME with stub commands.

PATH holds only the stubs and links to a short list of basic tools, so no real
`omarchy`, `omarchy-shell`, `secret-tool`, `nautilus` or `strata` is reachable.
"""
import json
import os
import pty
import re
import select
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
INSTALL = REPO / "scripts" / "install.sh"
PROGRAM = REPO / "bin" / "kindle-send"
PLUGIN_ID = "sorydi3.kindle-send"
BASIC_TOOLS = ["awk", "bash", "cat", "chmod", "cmp", "cp", "date", "dirname", "grep", "install", "ln", "mkdir",
               "mv", "python3", "readlink", "rm", "rmdir", "sed", "sleep"]


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
    for name in ("omarchy", "omarchy-shell", "secret-tool", "nautilus"):
        stub(bin_dir, name, f'echo "{name} $*" >> "{log}"\nexit 0\n')
    nautilus_python = tmp_path / "libnautilus-python.so"
    nautilus_python.write_text("")
    tools = tmp_path / "tools"
    basic_tools(tools)
    environ = {
        "KINDLE_SEND_NAUTILUS_PYTHON": str(nautilus_python),
        "HOME": str(home),
        "PATH": f"{bin_dir}:{tools}",
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
    }
    return {"home": home, "env": environ, "log": log, "bin": bin_dir, "tools": tools,
            "nautilus_python": nautilus_python}


def install(env, *args):
    return subprocess.run([str(env["tools"] / "bash"), str(INSTALL), *args], env=env["env"], cwd=env["home"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)


def calls(env):
    return env["log"].read_text().splitlines() if env["log"].exists() else []


def paths(env):
    home = env["home"]
    return {"bin": home / ".local" / "bin" / "kindle-send",
            "nautilus": home / ".local" / "share" / "nautilus-python" / "extensions" / "kindle-send.py",
            "strata": home / ".config" / "strata" / "actions" / "kindle-send",
            "old_program": home / ".local" / "share" / "kindle-send" / "bin" / "kindle-send"}


def with_strata(env):
    stub(env["bin"], "strata", "exit 0\n")


BINDINGS_TEXT = '-- mine\no.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh host")\n'
MENU_TEXT = ('{\n  // my menu\n  "snip": {"icon":"x","label":"Snip"},\n'
             '  "snip.rect": {"icon":"y","label":"Rect","action":"snip rect"}\n}\n')
# Opens the Picker in Settings, on no field in particular (spec §14).
SETTINGS_ACTION = "omarchy-shell shell summon sorydi3.kindle-send '{\"settings\":\"\"}'"
BIND_START = "-- >>> kindle-send keybinding (added by scripts/install.sh) >>>"
BIND_END = "-- <<< kindle-send <<<"
BIND_LINE = 'o.bind("SUPER + SHIFT + K", "Books to Kindle", "omarchy-shell shell toggle sorydi3.kindle-send")'


def config_files(env, bindings=BINDINGS_TEXT, menu=MENU_TEXT):
    config = env["home"] / ".config"
    b = config / "hypr" / "bindings.lua"
    m = config / "omarchy" / "extensions" / "omarchy-menu.jsonc"
    for path, text in ((b, bindings), (m, menu)):
        if text is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    return b, m


def shell_parse(text):
    """The menu file as omarchy-shell reads it (MenuModel.js stripJsonc + JSON.parse)."""
    stripped = re.sub(r"^\s*//[^\n]*(\n|$)", "", text, flags=re.M)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    return json.loads(stripped)


def run_tty(script, env, answers, *args):
    """Run a script with a terminal on stdin and stdout, typing `answers` in turn, one per prompt."""
    master, slave = pty.openpty()
    proc = subprocess.Popen([str(env["tools"] / "bash"), str(script), *args], env=env["env"], cwd=env["home"],
                            stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    out, typed = b"", 0
    while True:
        ready, _, _ = select.select([master], [], [], 10)
        if not ready:
            proc.kill()
            break
        try:
            chunk = os.read(master, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
        prompts = out.count(b"[y/N]") + out.count(b"[Y/n]")
        while typed < min(prompts, len(answers)):
            os.write(master, answers[typed].encode() + b"\n")
            typed += 1
    proc.wait(timeout=10)
    os.close(master)
    return proc.returncode, out.decode(errors="replace").replace("\r", "")


def snapshot(env):
    """Every file under HOME with its content (links as their target), to compare runs."""
    files = {}
    for path in sorted(env["home"].rglob("*")):
        key = str(path.relative_to(env["home"]))
        if path.is_symlink():
            files[key] = "-> " + os.readlink(path)
        elif path.is_file():
            files[key] = path.read_bytes()
    return files


# ---- dependencies

@pytest.mark.parametrize("tool", ["python3", "secret-tool"])
def test_a_missing_required_tool_stops_before_any_change(env, tool):
    target = env["bin"] / tool if (env["bin"] / tool).exists() else env["tools"] / tool
    target.unlink()
    config_files(env)
    before = snapshot(env)

    result = install(env, "--yes")

    assert result.returncode == 1
    assert tool in result.stderr
    assert snapshot(env) == before


def test_udisksctl_is_not_required(env):
    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert paths(env)["bin"].is_symlink()


def test_calibre_is_only_mentioned_and_sudo_never_run(env):
    stub(env["bin"], "sudo", f'echo "sudo $*" >> "{env['log']}"\nexit 1\n')

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert "Optional: sudo pacman -S calibre to send EPUB over USB" in result.stdout
    assert not any(line.startswith("sudo") for line in calls(env))


def test_calibre_note_is_left_out_when_it_is_installed(env):
    stub(env["bin"], "ebook-convert", "exit 0\n")

    result = install(env, "--yes")

    assert "Optional:" not in result.stdout


# ---- what it no longer does

def test_it_never_copies_or_enables_the_plugin(env):
    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    home = env["home"]
    assert not (home / ".local" / "share" / "kindle-send").exists()
    assert not (home / ".config" / "omarchy" / "plugins").exists()
    assert not any(line.startswith(("omarchy ", "omarchy-shell ")) for line in calls(env))


def test_no_real_omarchy_command_is_reachable(env):
    found = subprocess.run([str(env["tools"] / "bash"), "-c", "type -P omarchy-plugin-enable omarchy-shell-config"],
                           env=env["env"], capture_output=True, text=True)
    assert found.stdout == ""


# ---- asking

def test_without_a_terminal_nothing_is_changed_and_it_says_so(env):
    with_strata(env)
    config_files(env)
    before = snapshot(env)

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert snapshot(env) == before
    assert "no terminal to ask in" in result.stdout
    assert "--yes" in result.stdout
    assert "nautilus -q" not in calls(env)


def test_on_a_terminal_each_extra_is_asked_about_in_turn(env):
    b, m = config_files(env)

    # link, Nautilus, binding, menu, then the terminal setup offer
    code, out = run_tty(INSTALL, env, ["y", "n", "y", "n", "n"])

    assert code == 0, out
    p = paths(env)
    assert p["bin"].is_symlink()
    assert not p["nautilus"].exists()
    assert BIND_LINE in b.read_text()
    assert m.read_text() == MENU_TEXT
    assert out.count("[y/N]") == 5
    assert "Link ~/.local/bin/kindle-send" in out or f"Link {p['bin']}" in out


def test_declining_the_link_skips_the_right_click_extras_without_asking(env):
    with_strata(env)
    config_files(env)

    # link, binding, menu, setup offer: no question about Nautilus or Strata
    code, out = run_tty(INSTALL, env, ["n", "n", "n", "n"])

    assert code == 0, out
    p = paths(env)
    assert not p["bin"].exists()
    assert not p["nautilus"].exists()
    assert not p["strata"].exists()
    assert out.count("[y/N]") == 4
    assert "need the kindle-send link" in out


# ---- the link

def test_the_link_points_at_the_bundled_program_which_finds_the_test_epub(env):
    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    link = paths(env)["bin"]
    assert link.is_symlink()
    assert link.resolve() == PROGRAM.resolve()
    # test_epub_path(): <script realpath>/../assets/test.epub
    assert (link.resolve().parent.parent / "assets" / "test.epub").exists()


def test_an_older_installs_link_is_replaced_by_one_to_the_bundled_program(env):
    p = paths(env)
    p["old_program"].parent.mkdir(parents=True)
    shutil.copy(PROGRAM, p["old_program"])
    p["bin"].parent.mkdir(parents=True)
    p["bin"].symlink_to(p["old_program"])

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert p["bin"].resolve() == PROGRAM.resolve()


def test_an_older_installs_copied_command_is_replaced_by_the_link(env):
    p = paths(env)
    p["bin"].parent.mkdir(parents=True)
    shutil.copy(PROGRAM, p["bin"])

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert p["bin"].is_symlink()
    assert p["bin"].resolve() == PROGRAM.resolve()


def test_someone_elses_kindle_send_is_left_alone_and_the_right_click_extras_skipped(env):
    p = paths(env)
    p["bin"].parent.mkdir(parents=True)
    p["bin"].write_text("#!/bin/sh\necho someone else's\n")

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert p["bin"].read_text() == "#!/bin/sh\necho someone else's\n"
    assert "left alone" in result.stdout
    assert not p["nautilus"].exists()


# ---- right-click extras

def test_the_nautilus_extension_is_added_and_nautilus_reloaded(env):
    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert paths(env)["nautilus"].read_bytes() == (REPO / "nautilus" / "kindle-send.py").read_bytes()
    assert "nautilus -q" in calls(env)


def test_without_nautilus_python_the_nautilus_extension_is_skipped(env):
    env["nautilus_python"].unlink()
    b, _ = config_files(env)

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert not paths(env)["nautilus"].exists()
    assert "nautilus-python" in result.stdout
    assert "nautilus -q" not in calls(env)
    # The rest still goes in.
    assert paths(env)["bin"].is_symlink()
    assert BIND_LINE in b.read_text()


def test_with_strata_installed_its_action_is_added_disabled(env):
    with_strata(env)

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    text = (paths(env)["strata"] / "action.toml").read_text()
    assert 'program = "kindle-send"' in text and "enabled = false" in text
    assert "Settings → Actions" in result.stdout


def test_without_strata_no_action_is_added(env):
    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert not paths(env)["strata"].exists()


# ---- config edits

def test_yes_adds_the_keybinding_inside_markers_after_a_backup(env):
    b, _ = config_files(env)

    install(env, "--yes")

    text = b.read_text()
    assert text.startswith(BINDINGS_TEXT)
    assert text[len(BINDINGS_TEXT):].strip().splitlines() == [BIND_START, BIND_LINE, BIND_END]
    assert (b.parent / "bindings.lua.before-kindle-send").read_text() == BINDINGS_TEXT


def test_yes_adds_both_menu_entries_and_the_menu_still_parses(env):
    _, m = config_files(env)

    install(env, "--yes")

    menu = shell_parse(m.read_text())
    assert menu["snip.rect"]["action"] == "snip rect"
    assert menu["kindle-send"]["label"] == "Books to Kindle"
    assert menu["kindle-send.pick"]["label"] == "Books to Kindle"
    assert "action" not in menu["kindle-send"]  # a submenu
    assert menu["kindle-send.pick"]["action"] == "omarchy-shell shell toggle sorydi3.kindle-send"
    assert menu["kindle-send.settings"]["label"] == "Settings"
    assert menu["kindle-send.settings"]["action"] == SETTINGS_ACTION
    lines = m.read_text().splitlines()
    start = lines.index("  // >>> kindle-send menu (added by scripts/install.sh) >>>")
    end = lines.index("  // <<< kindle-send <<<")
    assert end - start == 4
    assert (m.parent / "omarchy-menu.jsonc.before-kindle-send").read_text() == MENU_TEXT


def test_a_missing_menu_file_is_created(env):
    _, m = config_files(env, menu=None)

    install(env, "--yes")

    assert set(shell_parse(m.read_text())) == {"kindle-send", "kindle-send.pick", "kindle-send.settings"}


def test_a_menu_file_that_does_not_parse_is_left_alone(env):
    broken = '{\n  "snip": {"label":"Snip"} // trailing comment breaks the shell\n}\n'
    _, m = config_files(env, menu=broken)

    result = install(env, "--yes")

    assert result.returncode == 0
    assert m.read_text() == broken
    assert "does not parse" in result.stderr


def test_an_edit_that_breaks_the_menu_is_rolled_back(env):
    # The last "}" sits in a comment, so the block lands in the wrong place.
    tricky = '{\n  "snip": {"label":"Snip"}\n}\n// end }\n'
    _, m = config_files(env, menu=tricky)

    result = install(env, "--yes")

    assert result.returncode == 0
    assert m.read_text() == tricky
    assert "put back" in result.stderr


# ---- re-running

def test_rerunning_changes_nothing(env):
    with_strata(env)
    config_files(env)
    install(env, "--yes")
    before, logged = snapshot(env), len(calls(env))

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert snapshot(env) == before
    assert result.stdout.count("Already") == 5  # link, Nautilus, Strata, binding, menu
    assert "nautilus -q" not in calls(env)[logged:]


def test_rerunning_on_a_terminal_asks_only_about_terminal_setup(env):
    with_strata(env)
    config_files(env)
    install(env, "--yes")
    before = snapshot(env)

    code, out = run_tty(INSTALL, env, ["n"])

    assert code == 0, out
    assert out.count("[y/N]") == 1
    assert "Set up in the terminal instead?" in out
    assert snapshot(env) == before


# The binding block an install before the rename to Books to Kindle left behind.
OLD_BINDING = ('-- mine\n\n' + BIND_START + '\n'
               'o.bind("SUPER + SHIFT + K", "Send to Kindle", "omarchy-shell shell toggle sorydi3.kindle-send")\n'
               + BIND_END + '\n-- after\no.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh host")\n')


def test_an_older_binding_block_is_replaced_in_place(env):
    b, _ = config_files(env, bindings=OLD_BINDING)

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert b.read_text() == OLD_BINDING.replace('"Send to Kindle"', '"Books to Kindle"')
    assert (b.parent / "bindings.lua.before-kindle-send").read_text() == OLD_BINDING
    assert "Updated" in result.stdout


def test_without_a_terminal_an_older_binding_block_is_left_as_it_is(env):
    b, _ = config_files(env, bindings=OLD_BINDING)

    install(env)

    assert b.read_text() == OLD_BINDING


def test_a_binding_block_without_its_end_marker_is_left_alone(env):
    broken = BINDINGS_TEXT + BIND_START + '\no.bind("SUPER + SHIFT + K", "x", "y")\n-- more of mine\n'
    b, _ = config_files(env, bindings=broken)

    result = install(env, "--yes")

    assert b.read_text() == broken
    assert "left alone" in result.stderr


# The menu block an install before Settings moved into the Picker left behind.
OLD_MENU_BLOCK = (
    '  // >>> kindle-send menu (added by scripts/install.sh) >>>\n'
    '  "kindle-send": {"icon":"\U000f00ba","label":"Send to Kindle","aliases":["kindle"]},\n'
    '  "kindle-send.pick": {"icon":"\U000f00ba","label":"Send to Kindle",'
    '"action":"omarchy-shell shell toggle sorydi3.kindle-send"},\n'
    '  "kindle-send.setup": {"icon":"","label":"Setup",'
    '"action":"omarchy-launch-floating-terminal-with-presentation kindle-send setup"},\n'
    '  // <<< kindle-send <<<\n')
MENU_WITH_OLD_BLOCK = ('{\n  // my menu\n  "snip": {"icon":"x","label":"Snip"},\n' + OLD_MENU_BLOCK +
                       '  "snip.rect": {"icon":"y","label":"Rect","action":"snip rect"}\n}\n')


def test_an_older_menu_block_is_replaced_in_place(env):
    _, m = config_files(env, menu=MENU_WITH_OLD_BLOCK)

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    text = m.read_text()
    menu = shell_parse(text)
    assert "kindle-send.setup" not in menu
    assert menu["kindle-send.settings"]["action"] == SETTINGS_ACTION
    assert menu["kindle-send"]["label"] == menu["kindle-send.pick"]["label"] == "Books to Kindle"
    assert text.count("kindle-send menu") == 1
    # In place: still between the user's own entries.
    assert text.index('"snip"') < text.index("kindle-send menu") < text.index('"snip.rect"')
    assert (m.parent / "omarchy-menu.jsonc.before-kindle-send").read_text() == MENU_WITH_OLD_BLOCK
    assert "Updated" in result.stdout


def test_without_a_terminal_an_older_menu_block_is_left_as_it_is(env):
    _, m = config_files(env, menu=MENU_WITH_OLD_BLOCK)

    install(env)

    assert m.read_text() == MENU_WITH_OLD_BLOCK


def test_an_older_nautilus_extension_is_updated_and_nautilus_reloaded(env):
    install(env, "--yes")
    p = paths(env)
    p["nautilus"].write_text("# older\n")
    logged = len(calls(env))

    install(env, "--yes")

    assert p["nautilus"].read_bytes() == (REPO / "nautilus" / "kindle-send.py").read_bytes()
    assert "nautilus -q" in calls(env)[logged:]


# ---- finish

def test_it_ends_by_pointing_to_the_bar_widget_and_offering_the_terminal_wizard(env):
    config_files(env)

    # link, binding, menu, setup offer
    code, out = run_tty(INSTALL, env, ["n", "y", "n", "n"])

    assert code == 0, out
    finish = out.split("==> Setup")[1]
    assert "bar widget" in finish
    assert "SUPER + SHIFT + K" in finish
    assert "Set up in the terminal instead? [y/N]" in finish


def test_without_the_binding_the_finish_does_not_mention_it(env):
    result = install(env)

    finish = result.stdout.split("==> Setup")[1]
    assert "bar widget" in finish
    assert "SUPER + SHIFT + K" not in finish
    assert "instead? [y/N]" not in result.stdout


def test_yes_on_the_terminal_offer_runs_the_bundled_wizard(env):
    fake = env["home"] / "plugin"
    shutil.copytree(REPO / "scripts", fake / "scripts")
    (fake / "nautilus").mkdir()
    shutil.copy(REPO / "nautilus" / "kindle-send.py", fake / "nautilus")
    (fake / "bin").mkdir()
    stub(fake / "bin", "kindle-send", f'echo "bundled $*" >> "{env['log']}"\n'
         'echo \'{"formats": ["epub"]}\'\n')
    env["nautilus_python"].unlink()

    # link, menu, then the terminal setup offer
    code, out = run_tty(fake / "scripts" / "install.sh", env, ["n", "n", "y"])

    assert code == 0, out
    assert "bundled setup" in calls(env)


# ---- options

def test_an_unknown_option_is_refused(env):
    result = install(env, "--frobnicate")

    assert result.returncode == 2
    assert "--help" in result.stderr


def test_help_names_the_options(env):
    result = install(env, "--help")

    assert result.returncode == 0
    for option in ("--yes", "--remove", "--purge"):
        assert option in result.stdout


# ---- --remove and --purge

def user_data(env):
    """Settings, a stored password and a Send history, as setup and Sends leave them."""
    home = env["home"]
    settings = home / ".config" / "kindle-send" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"kindleAddress": "reader@kindle.com"}')
    shell = home / ".config" / "omarchy" / "shell.json"
    shell.write_text('{"plugins": [{"id": "sorydi3.kindle-send", "kindleAddress": "reader@kindle.com"}]}')
    history = home / ".local" / "state" / "kindle-send" / "history.jsonl"
    history.parent.mkdir(parents=True)
    history.write_text('{"name":"Dune.epub"}\n')
    return settings, shell, history


def installed(env):
    with_strata(env)
    config_files(env)
    result = install(env, "--yes")
    assert result.returncode == 0, result.stderr
    return user_data(env)


def test_remove_takes_out_every_extra(env):
    installed(env)
    logged = len(calls(env))

    result = install(env, "--remove")

    assert result.returncode == 0, result.stderr
    p = paths(env)
    assert not p["bin"].exists() and not p["bin"].is_symlink()
    assert not p["nautilus"].exists()
    assert not p["strata"].exists()
    assert p["strata"].parent.exists()
    b, m = config_files(env, bindings=None, menu=None)
    assert b.read_text() == BINDINGS_TEXT
    assert "kindle-send" not in m.read_text()
    assert shell_parse(m.read_text()) == shell_parse(MENU_TEXT)
    assert "nautilus -q" in calls(env)[logged:]
    assert PROGRAM.exists()


def test_remove_keeps_settings_password_and_history_and_points_to_plugin_remove(env):
    settings, shell, history = installed(env)
    before = (settings.read_text(), shell.read_text())

    result = install(env, "--remove")

    assert (settings.read_text(), shell.read_text()) == before
    assert history.exists()
    assert not any(line.startswith("secret-tool") for line in calls(env))
    assert "--purge" in result.stdout
    assert f"omarchy plugin remove {PLUGIN_ID}" in result.stdout
    assert not any(line.startswith(("omarchy ", "omarchy-shell ")) for line in calls(env))


def test_purge_also_deletes_settings_password_and_history(env):
    settings, shell, history = installed(env)
    shell_before = shell.read_text()

    result = install(env, "--purge")

    assert result.returncode == 0, result.stderr
    assert not settings.parent.exists()
    assert not history.parent.exists()
    assert "secret-tool clear service kindle-send" in calls(env)
    assert shell.read_text() == shell_before  # nothing writes shell.json (ADR 0002)
    assert not paths(env)["bin"].is_symlink()
    assert (env["home"] / ".config" / "hypr" / "bindings.lua").read_text() == BINDINGS_TEXT


def test_remove_takes_out_an_older_installs_blocks_and_link(env):
    p = paths(env)
    p["old_program"].parent.mkdir(parents=True)
    shutil.copy(PROGRAM, p["old_program"])
    p["bin"].parent.mkdir(parents=True)
    p["bin"].symlink_to(p["old_program"])
    b, m = config_files(env, bindings=OLD_BINDING, menu=MENU_WITH_OLD_BLOCK)

    result = install(env, "--remove")

    assert result.returncode == 0, result.stderr
    assert not p["bin"].is_symlink()
    assert "kindle-send" not in b.read_text()
    assert "kindle-send" not in m.read_text()
    assert shell_parse(m.read_text()) == shell_parse(MENU_TEXT)


def test_remove_leaves_someone_elses_kindle_send_and_strata_action_alone(env):
    p = paths(env)
    p["bin"].parent.mkdir(parents=True)
    p["bin"].write_text("#!/bin/sh\necho someone else's\n")
    p["strata"].mkdir(parents=True)
    (p["strata"] / "action.toml").write_text('id = "kindle-send"\nprogram = "mine"\n')

    result = install(env, "--remove")

    assert result.returncode == 0, result.stderr
    assert p["bin"].exists()
    assert (p["strata"] / "action.toml").exists()
    assert "left alone" in result.stdout


@pytest.mark.parametrize("mode", ["--remove", "--purge"])
def test_remove_leaves_someone_elses_nautilus_extension_alone(env, mode):
    p = paths(env)
    p["nautilus"].parent.mkdir(parents=True)
    p["nautilus"].write_text("# someone else's kindle-send.py\n")

    result = install(env, mode)

    assert result.returncode == 0, result.stderr
    assert p["nautilus"].read_text() == "# someone else's kindle-send.py\n"
    assert f"{p['nautilus']} is not Books to Kindle's; left alone." in result.stdout
    assert "nautilus -q" not in calls(env)


def test_remove_takes_out_an_older_nautilus_extension_of_ours(env):
    p = paths(env)
    p["nautilus"].parent.mkdir(parents=True)
    p["nautilus"].write_text(f'"""Nautilus right-click "Send to Kindle"."""\nPLUGIN_ID = "{PLUGIN_ID}"\n')

    result = install(env, "--remove")

    assert result.returncode == 0, result.stderr
    assert not p["nautilus"].exists()


def test_remove_on_a_clean_home_succeeds_and_changes_nothing(env):
    before = snapshot(env)

    result = install(env, "--remove")

    assert result.returncode == 0, result.stderr
    assert snapshot(env) == before


def test_adding_after_remove_puts_each_block_in_once(env):
    installed(env)
    install(env, "--remove")

    install(env, "--yes")

    b, m = config_files(env, bindings=None, menu=None)
    assert b.read_text().count("kindle-send keybinding") == 1
    assert m.read_text().count("kindle-send menu") == 1
    assert paths(env)["bin"].is_symlink()


def test_the_old_uninstall_script_is_gone():
    assert not (REPO / "scripts" / "uninstall.sh").exists()
