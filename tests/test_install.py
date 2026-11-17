"""scripts/install.sh, run against a temp HOME with stub omarchy commands.

The real `omarchy` and `omarchy-shell` live in /usr/bin, so PATH must not
include it: it holds only the stubs and links to a short list of basic tools.
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
PLUGIN_ID = "sorydi3.kindle-send"
BASIC_TOOLS = ["awk", "bash", "cat", "chmod", "cp", "date", "dirname", "grep", "install", "ln", "mkdir",
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
    rescanned = tmp_path / "rescanned"
    stub(bin_dir, "omarchy-shell", f'echo "omarchy-shell $*" >> "{log}"\n'
         f'[[ "$*" == *rescanPlugins* ]] && : > "{rescanned}"\nexit 0\n')
    # `plugin list` shows the plugin only once the shell has rescanned.
    stub(bin_dir, "omarchy", f'echo "omarchy $*" >> "{log}"\n'
         f'if [[ "$1 $2" == "plugin list" ]]; then\n'
         f'  [[ -f "{rescanned}" ]] && echo \'[{{"id":"{PLUGIN_ID}"}}]\' || echo "[]"\n'
         f'fi\nexit 0\n')
    for name in ("secret-tool", "udisksctl", "nautilus"):
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
    copy = home / ".local" / "share" / "kindle-send" / "omarchy-plugin"
    return {"bin": home / ".local" / "bin" / "kindle-send", "copy": copy,
            "link": home / ".config" / "omarchy" / "plugins" / PLUGIN_ID}


def test_install_copies_the_command_and_plugin_and_links_the_plugin(env):
    result = install(env)

    assert result.returncode == 0, result.stderr
    p = paths(env)
    assert p["bin"].read_bytes() == (REPO / "bin" / "kindle-send").read_bytes()
    assert os.access(p["bin"], os.X_OK)
    plugin_files = ["manifest.json", *[f.name for f in REPO.glob("*.qml")], *[f.name for f in REPO.glob("*.js")]]
    assert {"Picker.qml", "Service.qml", "Rows.js"} <= set(plugin_files)
    for name in plugin_files:
        assert (p["copy"] / name).read_bytes() == (REPO / name).read_bytes()
    # The plugin files only, not the rest of the repo.
    assert sorted(f.name for f in p["copy"].iterdir()) == sorted(plugin_files)
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


@pytest.mark.parametrize("tool", ["python3", "secret-tool", "udisksctl"])
def test_a_missing_dependency_stops_install_before_copying_anything(env, tool):
    target = env["bin"] / tool if (env["bin"] / tool).exists() else env["tools"] / tool
    target.unlink()

    result = install(env)

    assert result.returncode == 1
    assert tool in result.stderr
    assert not paths(env)["bin"].exists()
    assert not paths(env)["copy"].exists()


def test_missing_nautilus_python_stops_install(env):
    env["nautilus_python"].unlink()

    result = install(env)

    assert result.returncode == 1
    assert "nautilus-python" in result.stderr
    assert "sudo pacman -S nautilus-python" in result.stderr
    assert not paths(env)["bin"].exists()


def test_calibre_is_only_mentioned_and_sudo_never_run(env):
    stub(env["bin"], "sudo", f'echo "sudo $*" >> "{env['log']}"\nexit 1\n')

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert "Optional: sudo pacman -S calibre to send EPUB over USB" in result.stdout
    assert not any(line.startswith("sudo") for line in calls(env))


def test_calibre_note_is_left_out_when_it_is_installed(env):
    stub(env["bin"], "ebook-convert", "exit 0\n")

    result = install(env)

    assert "Optional:" not in result.stdout


# ---- what the installed command finds

def test_installed_command_links_to_a_copy_beside_its_assets(env):
    install(env)

    p = paths(env)
    data = env["home"] / ".local" / "share" / "kindle-send"
    assert p["bin"].is_symlink()
    real = p["bin"].resolve()
    assert real == data / "bin" / "kindle-send"
    # test_epub_path(): <script realpath>/../assets/test.epub
    assert (real.parent.parent / "assets" / "test.epub").read_bytes() == (REPO / "assets" / "test.epub").read_bytes()


def test_install_replaces_a_command_copied_by_an_older_install(env):
    p = paths(env)
    p["bin"].parent.mkdir(parents=True)
    p["bin"].write_text("old copy")

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert p["bin"].is_symlink()


# ---- Nautilus

def test_nautilus_extension_is_installed_and_nautilus_restarted(env):
    install(env)

    ext = env["home"] / ".local" / "share" / "nautilus-python" / "extensions" / "kindle-send.py"
    assert ext.read_bytes() == (REPO / "nautilus" / "kindle-send.py").read_bytes()
    assert "nautilus -q" in calls(env)


# ---- config edits

BINDINGS_TEXT = '-- mine\no.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh host")\n'
MENU_TEXT = ('{\n  // my menu\n  "snip": {"icon":"x","label":"Snip"},\n'
             '  "snip.rect": {"icon":"y","label":"Rect","action":"snip rect"}\n}\n')
# Opens the Picker in Settings, on no field in particular (spec §14).
SETTINGS_ACTION = "omarchy-shell shell summon sorydi3.kindle-send '{\"settings\":\"\"}'"
BIND_LINE = 'o.bind("SUPER + SHIFT + K", "Send to Kindle", "omarchy-shell shell toggle sorydi3.kindle-send")'


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


def test_without_a_terminal_config_is_left_alone_and_install_says_so(env):
    b, m = config_files(env)

    result = install(env)

    assert result.returncode == 0, result.stderr
    assert b.read_text() == BINDINGS_TEXT
    assert m.read_text() == MENU_TEXT
    assert result.stdout.count("no terminal to ask in") == 2
    assert "--yes" in result.stdout


def test_yes_adds_the_keybinding_inside_markers_after_a_backup(env):
    b, _ = config_files(env)

    install(env, "--yes")

    text = b.read_text()
    assert text.startswith(BINDINGS_TEXT)
    block = text[len(BINDINGS_TEXT):].strip().splitlines()
    assert block == ["-- >>> kindle-send keybinding (added by scripts/install.sh) >>>", BIND_LINE,
                     "-- <<< kindle-send <<<"]
    assert (b.parent / "bindings.lua.before-kindle-send").read_text() == BINDINGS_TEXT


def test_yes_adds_both_menu_entries_and_the_menu_still_parses(env):
    _, m = config_files(env)

    install(env, "--yes")

    menu = shell_parse(m.read_text())
    assert menu["snip.rect"]["action"] == "snip rect"
    assert menu["kindle-send"]["label"] == "Send to Kindle"
    assert "action" not in menu["kindle-send"]  # a submenu
    assert menu["kindle-send.pick"]["action"] == "omarchy-shell shell toggle sorydi3.kindle-send"
    assert menu["kindle-send.settings"]["label"] == "Settings"
    assert menu["kindle-send.settings"]["action"] == SETTINGS_ACTION
    assert "kindle-send.setup" not in menu
    lines = m.read_text().splitlines()
    start = lines.index("  // >>> kindle-send menu (added by scripts/install.sh) >>>")
    end = lines.index("  // <<< kindle-send <<<")
    assert end - start == 4
    assert (m.parent / "omarchy-menu.jsonc.before-kindle-send").read_text() == MENU_TEXT


def test_a_missing_menu_file_is_created(env):
    _, m = config_files(env, menu=None)

    install(env, "--yes")

    assert set(shell_parse(m.read_text())) == {"kindle-send", "kindle-send.pick", "kindle-send.settings"}


def test_rerunning_install_does_not_duplicate_the_config_blocks(env):
    b, m = config_files(env)
    install(env, "--yes")
    first = (b.read_text(), m.read_text())

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    assert (b.read_text(), m.read_text()) == first
    assert result.stdout.count("Already in") == 2


# The menu block an install before Settings moved into the Picker left behind.
OLD_MENU_BLOCK = (
    '  // >>> kindle-send menu (added by scripts/install.sh) >>>\n'
    '  "kindle-send": {"icon":"\U000f00ba","label":"Send to Kindle","aliases":["kindle"]},\n'
    '  "kindle-send.pick": {"icon":"\U000f00ba","label":"Send to Kindle",'
    '"action":"omarchy-shell shell toggle sorydi3.kindle-send"},\n'
    '  "kindle-send.setup": {"icon":"","label":"Setup",'
    '"action":"omarchy-launch-floating-terminal-with-presentation kindle-send setup"},\n'
    '  // <<< kindle-send <<<\n')
MENU_WITH_OLD_BLOCK = ('{\n  // my menu\n  "snip": {"icon":"x","label":"Snip"},\n' + OLD_MENU_BLOCK +
                       '  "snip.rect": {"icon":"y","label":"Rect","action":"snip rect"}\n}\n')


def test_reinstalling_over_an_old_install_replaces_its_setup_entry_in_place(env):
    _, m = config_files(env, menu=MENU_WITH_OLD_BLOCK)

    result = install(env, "--yes")

    assert result.returncode == 0, result.stderr
    text = m.read_text()
    menu = shell_parse(text)
    assert "kindle-send.setup" not in menu
    assert menu["kindle-send.settings"]["action"] == SETTINGS_ACTION
    assert text.count("kindle-send menu") == 1
    # In place: still between the user's own entries.
    assert text.index('"snip"') < text.index("kindle-send menu") < text.index('"snip.rect"')
    assert menu["snip.rect"]["action"] == "snip rect"
    assert (m.parent / "omarchy-menu.jsonc.before-kindle-send").read_text() == MENU_WITH_OLD_BLOCK
    assert "Updated" in result.stdout


def test_without_a_terminal_an_old_menu_block_is_left_as_it_is(env):
    _, m = config_files(env, menu=MENU_WITH_OLD_BLOCK)

    result = install(env)

    assert m.read_text() == MENU_WITH_OLD_BLOCK
    assert "no terminal to ask in" in result.stdout


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


def test_no_config_skips_the_edits(env):
    b, m = config_files(env)

    install(env, "--no-config")

    assert (b.read_text(), m.read_text()) == (BINDINGS_TEXT, MENU_TEXT)


def test_on_a_terminal_each_edit_is_asked_about(env):
    b, m = config_files(env)

    code, out = run_tty(INSTALL, env, ["y", "n", "n"])

    assert code == 0, out
    assert "Add SUPER + SHIFT + K" in out
    assert BIND_LINE in b.read_text()
    assert m.read_text() == MENU_TEXT


PICKER_SETUP = "Press SUPER + SHIFT + K to set up Send to Kindle in the Picker"
TERMINAL_SETUP = "Or set up in the terminal instead: kindle-send setup"


def test_install_ends_by_pointing_to_the_picker_and_offering_the_terminal_wizard(env):
    config_files(env)

    code, out = run_tty(INSTALL, env, ["n", "n", "n"])

    assert code == 0, out
    finish = out.split("==> Setup")[1]
    assert PICKER_SETUP in finish
    assert "Set up in the terminal instead? [y/N]" in finish
    assert TERMINAL_SETUP in finish
    assert "Run setup now" not in out


def test_without_a_terminal_install_points_to_the_picker_and_the_terminal_wizard(env):
    result = install(env)

    finish = result.stdout.split("==> Setup")[1]
    assert PICKER_SETUP in finish
    assert TERMINAL_SETUP in finish
    assert "instead? [y/N]" not in result.stdout


# ---- Strata

def strata_action(env):
    return env["home"] / ".config" / "strata" / "actions" / "kindle-send" / "action.toml"


def test_with_strata_installed_its_action_is_added_disabled(env):
    stub(env["bin"], "strata", "exit 0\n")

    result = install(env)

    assert result.returncode == 0, result.stderr
    text = strata_action(env).read_text()
    assert 'program = "kindle-send"' in text and "enabled = false" in text
    assert "Settings → Actions" in result.stdout


def test_without_strata_no_action_is_added(env):
    result = install(env)

    assert result.returncode == 0, result.stderr
    assert not strata_action(env).exists()
