# How third-party Omarchy plugins ship helpers, keybindings and dependencies

Research for [#47](https://github.com/sorydi3/kindle-send/issues/47) (map [#46](https://github.com/sorydi3/kindle-send/issues/46)). Done 2026-11-13 against the Omarchy install on the author's machine (`/usr/share/omarchy`), the Omarchy manual, and public plugin repos on GitHub. Nothing was installed, enabled or edited.

## Answer

- **Helper programs:** a plugin ships its helper inside its own folder and runs it by absolute path through a Quickshell `Process`. `git clone` keeps the exec bit (mode `100755` in the tree), and nothing in the validator rejects non-QML files. Every published example does this: joamag's `docker.sh`, Jankees's `bin/downloads`.
- **Finding its own folder:** `Qt.resolvedUrl("relative/path")` from the QML file, with the `file://` stripped. That is what the published plugins do. The shell also passes a `manifest` property that keeps `__sourceDir` "so third-party plugins find their bundled scripts through it".
- **Keybinding and menu entry:** no plugin gets one automatically. Omarchy has no manifest field or install hook for either. Published plugins print an `o.bind(...)` line in their README for the user to paste into `~/.config/hypr/bindings.lua`. One (Omamail) writes a marked block into `bindings.lua` from its own Settings, with an Undo.
- **Outside dependencies:** the manifest has no field for them. Plugins say what they need in the README ("Requires Omarchy 4 and …") and handle a missing tool at run time: joamag.docker hides itself when the Docker CLI is missing.
- **`update`:** fetches `origin HEAD`, shows the diff, fast-forwards only, validates again and rolls back on failure. It never touches `shell.json`.
- **`remove`:** disables the plugin first, which deletes its `shell.json` entry and the Settings stored inline on that entry. Then it `rm -rf`s a git checkout.

## 1. What `omarchy plugin add` copies and checks

`omarchy-plugin-add` clones into a staging folder, validates it, and moves the whole clone (including `.git`) into place:

```bash
stage="$PLUGINS_DIR/.add.tmp.$$"
...
if ! git clone -- "$url" "$stage"; then
...
if ! omarchy-plugin-validate "$stage"; then
...
mv "$stage" "$target"
echo "Added $id into $target"

omarchy-shell shell rescanPlugins >/dev/null
```
— `/usr/share/omarchy/bin/omarchy-plugin-add` lines 119–150

So the installed plugin **is** a git checkout of the whole repo. Every tracked file arrives, not just QML. The manual: "It never runs anything from the plugin, never executes an install hook, and never asks for sudo" ([omarchy.org/manual/shell-plugins](https://omarchy.org/manual/shell-plugins/)).

### What the validator checks (the full list)

`omarchy-plugin-validate` checks, in order: `manifest.json` exists and is JSON; `schemaVersion == 1`; the fields `id name version kinds entryPoints` are there; the id matches `^[A-Za-z0-9][A-Za-z0-9._-]*$`, has no `..` and is not `omarchy.*`; `kinds` is a non-empty array; `entryPoints` is an object; `barWidget.defaultSection` is a known section; each entry point is relative, has no `..` and exists as a file; each kind that needs an entry point has one; and:

```bash
# Refuse any symlink anywhere inside the plugin folder. ...
# The .git dir is skipped: installed plugins are git
# checkouts, and git's internals are never loaded by the shell.
link=$(find "$PLUGIN_DIR" -name .git -prune -o -type l -print -quit 2>/dev/null)
[[ -z $link ]] || fail "symlinks are not allowed inside a plugin folder: $link"
```
— `/usr/share/omarchy/bin/omarchy-plugin-validate` lines 111–116

**There is no rule about file types, executables or non-QML files.** Symlinks are the only content rule. Unknown manifest fields are ignored: `validateManifest` in `/usr/share/omarchy/shell/services/PluginRegistry.qml` (lines 43–90) checks only the same fields.

## 2. Shipping and running a helper program

### The exec bit survives

Git stores the mode per file, and `git clone` checks it out with that mode. Published plugins rely on this. Their helpers are tracked `100755` and run directly with no `bash`/`python3` in front:

| Repo | Tracked file | How it is run |
|---|---|---|
| [joamag/omarchy-plugins](https://github.com/joamag/omarchy-plugins) `plugins/joamag.docker/` | `100755 docker.sh` | `command: [root.scriptPath]` |
| [jankeesvw/omarchy-downloads](https://github.com/jankeesvw/omarchy-downloads) (root manifest, installed with `omarchy plugin add`) | `100755 bin/downloads` | `probeProc.command = [root.helper, "probe", root.folderPath]` |
| [Jodarini/omarchy-plugins](https://github.com/Jodarini/omarchy-plugins) `jodarini.downloads/` (fork of the above) | `100755 bin/downloads` | same |

(Modes from `gh api repos/<repo>/git/trees/HEAD?recursive=1`.)

joamag's repo states it as a convention: "Helper scripts ship inside the plugin folder and are resolved from the QML file location, never from `$OMARCHY_PATH`." ([README](https://github.com/joamag/omarchy-plugins/blob/HEAD/README.md), Conventions)

The shell's own file watcher allows for Python helpers inside plugin folders:

```js
// Bytecode a plugin's Python helper writes on import would otherwise reload it, restart the helper, and loop.
if (/\/__pycache__(\/|$)/.test(relative)) return ""
```
— `PluginRegistry.qml` lines 800–801

For kindle-send: `bin/kindle-send` is already tracked `100755` with a `#!/usr/bin/env python3` shebang. Shipped inside the plugin folder, it can be run as `[<plugin dir>/bin/kindle-send, "plan"]` the way the Service and Picker run `["kindle-send", …]` today. Today's `["kindle-send", …]` commands depend on `PATH`, and `plugin add` puts nothing on `PATH`.

### Finding the plugin's own folder at run time

**`Qt.resolvedUrl`, used by every published plugin.** It resolves relative to the QML file that calls it:

```qml
readonly property string scriptPath: String(Qt.resolvedUrl("docker.sh")).replace(/^file:\/\//, "")
```
— joamag.docker `Panel.qml` line 29

```qml
readonly property string helper:
  Qt.resolvedUrl("bin/downloads").toString().replace(/^file:\/\//, "")
```
— jodarini.downloads `DownloadsStore.qml` lines 467–468

Caveat: this gives a URL, so a path with spaces or non-ASCII characters comes out percent-encoded. `~/.config/omarchy/plugins/<id>/` has none unless `$HOME` does.

**`manifest.__sourceDir`, which the shell hands to the plugin.** Any plugin root object that declares a `manifest` property gets a copy of its manifest. That covers menu, panel and overlay items (`shell.qml` line 1408) and services (line 959). The shell removes only its trust markers:

```js
function publicPluginManifest(manifest) {
  ...
  // Keep __sourceDir: third-party plugins find their bundled scripts through it.
  // Only the host trust markers are withheld.
  delete copy.__isFirstParty
  delete copy.__hostCapabilities
```
— `/usr/share/omarchy/shell/shell.qml` lines 329–338

`__sourceDir` is the plugin's absolute folder, set when the registry scans (`manifest.__sourceDir = currentSource`, `PluginRegistry.qml` line 621). kindle-send's `Service.qml` already declares `manifest` (it reads `manifest.id`). `manifest.__sourceDir + "/bin/kindle-send"` is a plain path with no URL encoding, but the leading `__` marks it as host-internal. `Qt.resolvedUrl` is the pattern published plugins actually use.

### Writing inside the plugin folder is a bad idea

Two facts in the sources rule it out. The watcher reloads a plugin on any `close_write,create,delete,move` under `~/.config/omarchy/plugins/<id>/` (`PluginRegistry.qml` lines 726–745, 791–805). And `remove` deletes the folder (section 5). kindle-send already keeps its Send history under `$XDG_STATE_HOME/kindle-send` (`bin/kindle-send` `state_dir()`), so this needs no change.

## 3. Keybindings and Omarchy menu entries

Omarchy gives a plugin no way to add a keybinding or a menu entry. The manifest schema has no such field, `add` runs no hooks (section 1), and the menu reads only two files: "defaults: `default/omarchy/omarchy-menu.jsonc`; user extensions: `~/.config/omarchy/extensions/omarchy-menu.jsonc`" (`/usr/share/omarchy/shell/plugins/README.md`, "Omarchy menu"). Every published plugin found leaves the binding to the user:

- **jankeesvw.downloads**, "A key for it":
  ```lua
  o.bind("SUPER + D", "Downloads", "omarchy-shell shell toggle jankeesvw.downloads")
  ```
  ([README](https://github.com/jankeesvw/omarchy-downloads/blob/HEAD/README.md)). It also tells the user to delete things they added by hand: "If you added Hyprland window rules for an older version, remove those separately from your Hyprland configuration."
- **joamag.docker** binds nothing. Its right-click reuses Omarchy's own "`SUPER + SHIFT + D`" target, `omarchy-launch-or-focus-tui omarchy-launch-docker-tui` (plugin `README.md`, `Panel.qml` line 80).
- **Omarchy-Spotify** (`stappmus/Omarchy-Spotify`): "To replace Omarchy's existing **Super+Shift+M · Music** binding, add this to `~/.config/hypr/bindings.lua`" with `hl.unbind(...)` + `o.bind(...)`. Its setting description says the feature "Requires the one-time bindings.lua override from the README".
- **Omamail** (`huacnlee/omamail`) is the one plugin that edits the file itself, and only on request from its own Settings: "The key bindings go in a clearly marked block in `~/.config/hypr/bindings.lua`; Omarchy's own files are never changed. **Undo** removes the block and leaves the file as it was." Its manual fallback: `o.bind("SUPER + SHIFT + G", "Omamail", "omarchy shell shell toggle omamail '{}'")`.

No published plugin found adds an Omarchy menu entry. The pattern for kindle-send's keybinding is the README `o.bind` line, `omarchy-shell shell toggle sorydi3.kindle-send`, which `scripts/install.sh` already writes. A marked block written from Settings, as Omamail does, is the precedent if the user should not have to edit files.

## 4. Outside dependencies

No manifest field declares a dependency, and Omarchy checks none. Published plugins do two things:

1. **Say it in the README.** Omamail: "The plugin requires **Omarchy 4**". Spotify: "Requires Omarchy 4 and a personal Spotify Premium account." Downloads: "with one local helper script (`bin/downloads`) that only very large folders … fall back to."
2. **Handle a missing tool at run time.** joamag.docker's states table: "Docker CLI missing | widget hidden", "Daemon not running | dimmed icon | 'Start daemon' button". `docker.sh` "checks the CLI and the socket permission" first (plugin README). kindle-send's Picker already does the same with its `"missing"` listing state ("no kindle-send").

Heavier plugins fetch their backends after install, from the plugin's own UI. Omamail: "install the pinned backend when prompted". Spotify: "Local playback installs an exact-version backend only after its GitHub build provenance matches this plugin version's tag". Spotify also ships a `scripts/uninstall.sh` in the plugin folder for what `remove` leaves behind: "Run the bundled uninstaller from outside the plugin directory".

## 5. What `update`, `disable` and `remove` do

### `omarchy plugin update [id]`

```bash
if ! git -C "$dir" fetch --quiet origin HEAD; then
...
  git -C "$dir" diff HEAD FETCH_HEAD          # shown, then "Update $id?" unless --yes
...
if ! git -C "$dir" merge --ff-only FETCH_HEAD >/dev/null 2>&1; then
  echo "... cannot fast-forward '$id'; you have local changes in $dir" >&2
...
if ! omarchy-plugin-validate "$dir"; then
  git -C "$dir" reset --hard ORIG_HEAD >/dev/null
  echo "... update of '$id' failed validation; rolled back" >&2
```
— `/usr/share/omarchy/bin/omarchy-plugin-update` lines 43–76

It follows the remote's default branch (`origin HEAD`), not tags, and doesn't read the manifest `version`. Files change only through git, so modes (the exec bit) follow the repo. It refuses to update a folder without `.git` ("not a git checkout, so there is nothing to pull from"). Its only shell call is `rescanPlugins`, so `shell.json` is left alone and Settings survive an update.

### `omarchy plugin disable <id>`

Runs `omarchy-shell shell setPluginEnabled "$id" false` (`omarchy-plugin-disable` line 22). For a third-party non-bar plugin, `setEnabled(…, false)` removes its record from `plugins[]`:

```js
else if (location.kind === "plugin") config.plugins.splice(location.index, 1)
```
— `PluginRegistry.qml` line 589

That record is where inline Settings live. `updateEntryInline` writes the settings onto the same `{ id, … }` object in `plugins[]` (`shell.qml` lines 1102–1140), and kindle-send's own Settings live there too (spec, "Settings live inline on the plugin's entry in `~/.config/omarchy/shell.json`"). **Disabling deletes the Settings.** The keyring password and `$XDG_STATE_HOME/kindle-send` are outside Omarchy's reach and survive.

The other direction holds too. A third-party plugin "is enabled exactly when its id appears somewhere in that file" (manual; `isEnabled` → `findEntryLocation`, `PluginRegistry.qml` lines 148–164, 234–251). So `kindle-send save` writing a `plugins[]` entry for a plugin that isn't enabled would turn it on.

### `omarchy plugin remove <id>`

```bash
if [[ $was_enabled == "true" ]]; then
  omarchy-shell shell setPluginEnabled "$id" false >/dev/null
fi

if [[ -L $target ]]; then
  rm -f "$target"
  echo "Unlinked $id."
elif [[ -d $target/.git ]]; then
  rm -rf "$target"
  echo "Removed $id."
else
  base="$PLUGINS_DIR/.${id}.bak.$(date -u +%Y%m%d%H%M%S)"
  ...
  mv "$target" "$backup" || fail "failed to move $target to backup"
```
— `/usr/share/omarchy/bin/omarchy-plugin-remove` lines 95–115

So `remove` = disable (Settings entry deleted, as above) + delete the folder. A `plugin add` install is a git checkout, so the folder is gone with no backup. A symlinked folder (today's `install.sh` install) is only unlinked, and a plain copied folder is moved to `.<id>.bak.<timestamp>`. The jodarini.downloads README agrees: "the entry in `~/.config/omarchy/shell.json`, removed by the command above".

### `omarchy plugin enable <id>`

Runs `omarchy-shell shell enablePlugin "$id" "$placement"` (`omarchy-plugin-enable` line 85). For a menu/service plugin this pushes a bare `{ id }` onto `plugins[]` when there is no entry yet (`PluginRegistry.qml` lines 556–575), so a re-enabled plugin starts with empty Settings.

## 6. Repo layout precedent

`plugin add` needs `manifest.json` at the repo root, and multi-plugin repos don't meet that. joamag publishes each plugin by splitting it into its own repo: "`omarchy plugin add <git-url>` expects `manifest.json` at the repository root, so a plugin is published by splitting its folder into a standalone repo: `git subtree split --prefix=plugins/joamag.sysmon …`" ([README](https://github.com/joamag/omarchy-plugins/blob/HEAD/README.md), "Publishing a plugin"). Jodarini instead makes the whole `~/.config/omarchy/plugins` a checkout with its own installer (`.sync/install.sh`), which is outside the `plugin add` path. Jankees's `omarchy-downloads` is the plain single-plugin shape: manifest, QML and `bin/downloads` at the root, plus `README.md`, `LICENSE`, `preview.png` and `screenshots/`.

The manual names the listing: "To help people actually find it, list it at plugins.omarchy.org."

## Sources

- `/usr/share/omarchy/bin/omarchy-plugin-{add,update,remove,validate,enable,disable}`
- `/usr/share/omarchy/shell/services/PluginRegistry.qml`, `PluginRegistryApi.qml`, `PluginShellApi.qml`; `/usr/share/omarchy/shell/shell.qml`
- `/usr/share/omarchy/shell/plugins/README.md`, `/usr/share/omarchy/shell/README.md` (its links to `docs/omarchy-shell.md` and `manual/32-shell-plugins.md` point at files not installed on this machine)
- `/usr/share/omarchy/default/agents/skills/omarchy/plugins.md`
- Omarchy manual, [Shell plugins](https://omarchy.org/manual/shell-plugins/)
- [joamag/omarchy-plugins](https://github.com/joamag/omarchy-plugins): `README.md`, `plugins/joamag.docker/{manifest.json,README.md,Panel.qml}`, `bin/package`
- [Jodarini/omarchy-plugins](https://github.com/Jodarini/omarchy-plugins): `README.md`, `.sync/install.sh`, `jodarini.downloads/{manifest.json,README.md,DownloadsStore.qml}`
- [jankeesvw/omarchy-downloads](https://github.com/jankeesvw/omarchy-downloads): `README.md`, `manifest.json`, tree modes
- [huacnlee/omamail](https://github.com/huacnlee/omamail) and [stappmus/Omarchy-Spotify](https://github.com/stappmus/Omarchy-Spotify): `README.md`, `manifest.json`
