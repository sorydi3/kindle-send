# What an omarchy-shell `menu` and `service` plugin can do

Answers ticket `.scratch/kindle-send/issues/03-plugin-api-facts.md`.
Sources are the installed Omarchy shell (Quickshell 0.3.2, `qs --version`) under
`/usr/share/omarchy/shell` and `/usr/share/omarchy/bin`, plus the plugins
installed in `~/.config/omarchy/plugins/`. Line numbers refer to those files as
installed on 2026-11-04.

## TL;DR

- A plugin is a directory `~/.config/omarchy/plugins/<id>/` with `manifest.json`
  and QML entry points. One plugin can declare several kinds at once, e.g.
  `["bar-widget", "menu", "service"]` (sorydi3.window-restore).
- The **menu** kind is not a widget kit. It is an arbitrary QML `Item` that the shell
  loads on summon and calls `open(payloadJson)` / `close()` on. The plugin draws
  its own `PanelWindow` (layer-shell). Lists, search-as-you-type and key handling
  are all hand-written; window-restore's `Picker.qml` is a complete working example.
- A **service** is a headless QML object, loaded at startup while enabled. It
  runs external programs with `Quickshell.Io` `Process` (argv, stdout parsers,
  exit codes) or `Quickshell.execDetached`. Omarchy gives plugins no notification
  API. Plugins shell out to `notify-send` / `omarchy-notification-send`.
- **Settings** go inline on the plugin's entry in `~/.config/omarchy/shell.json`
  (`plugins[]`). The shell does not inject them into a menu or service, so the plugin
  reads `shell.json` itself (key-promoter uses a `FileView`). It writes them back
  with the scoped `shell.updateEntryInline(ownId, settings)`.
- **Opening it**: `omarchy-shell shell toggle <id> '<json>'`, from a Hyprland
  bind, an `omarchy-menu.jsonc` `action`, or any script.
- **External triggers work**: anything in the user session (a Nautilus script
  included) can run `omarchy-shell shell summon|toggle <id> '<json>'`, and
  `omarchy-shell shell call <id> <method> <arg>` for a loaded menu/panel item.
  A plugin can also register its own `IpcHandler { target: "..." }` and
  is then reachable as `omarchy-shell <target> <fn> args…`. key-promoter does this
  from a third-party service.

## 1. Manifest schema

Validated by `validateManifest` in `/usr/share/omarchy/shell/services/PluginRegistry.qml:43-90`
and mirrored by `/usr/share/omarchy/bin/omarchy-plugin-validate:38-116`.

| Field | Rule | Source |
|---|---|---|
| `schemaVersion` | must be the number `1` | PluginRegistry.qml:48; validate:41 |
| `id`, `name`, `version`, `kinds`, `entryPoints` | required | PluginRegistry.qml:52-58 |
| `id` | `^[A-Za-z0-9][A-Za-z0-9._-]*$`, no `..`, not `omarchy.*` (reserved) | validate:49-53; PluginRegistry.qml:627-630 |
| `kinds` | non-empty array of `bar-widget`, `panel`, `overlay`, `menu`, `service`, `bar` | PluginRegistry.qml:64; README.md:74-83 |
| `entryPoints` | object; key per kind: `menu`, `service`, `barWidget`, `panel`, `overlay`, `bar`. Relative paths, no `..`, must exist | validate:97-109, 79-87; PluginRegistry.qml:82-88 |
| `keepLoaded` | `true` keeps menu/panel mounted between summons, and keeps a service alive across hot-reload (code changes then need a shell restart) | README.md:87-94; shell.qml:1027-1053, 1340 |
| `barWidget` | `displayName`, `category`, `allowMultiple`, `defaultSection` (left/center/right), `defaults`, `schema` | README.md:61-70; PluginRegistry.qml:72-79 |
| `author`, `description` | optional, informational | README.md:57-58 |
| `omarchy.clonedFrom`, `omarchy.capabilities` | used by built-in clones and first-party trust only | PluginRegistry.qml:92-116 |

Symlinks *inside* the plugin folder are refused by the validator (validate:115-116).
window-restore's plugin directory is itself a symlink
(`~/.config/omarchy/plugins/sorydi3.window-restore -> ~/.local/share/window-restore/omarchy-plugin`),
and it loads.

Example manifest with menu + service + widget:
`~/.config/omarchy/plugins/sorydi3.window-restore/manifest.json`.

## 2. Lifecycle and what gets injected

**Menu / panel / overlay** (`shell.qml:1296-1369`):
- There is one `Loader` per enabled plugin of those kinds. It is active while summoned, or always if `keepLoaded` is set (1340).
- After load the shell sets these properties if the item declares them: `omarchyPath`, `shell` (scoped facade),
  `manifest`, `barWidgetRegistry`, `pluginRegistry`. It also sets `service`, which is
  the same plugin's service instance (1344-1352).
- `summon` queues the payload string and calls `item.open(payloadJson)` (1155-1193, 1256-1271).
  `hide` calls `item.close()` (1195-1210, 1204). `toggle` uses `item.opened` to tell
  whether the item is open (1212-1228). So a menu should expose `property bool opened`,
  `function open(payloadJson)` and `function close()`, as Picker.qml does (lines 19, 46-60).

**Service** (`shell.qml:904-1025`):
- It is created with `Qt.createComponent` when enabled. A third-party service gets no visual parent (926).
- The same properties are injected (931-935). It is published in `_services[id]`, and the plugin's own
  widget or menu gets it via `shell.serviceFor(ownId)` (889-891, 394-397).
- Disabling or removing the plugin destroys the service (995-1009).

**Scoped `shell` facade for third-party plugins** (`services/PluginShellApi.qml`,
built in `shell.qml:572-677`):
- `serviceFor(id)`, `summon/hide/toggle/isPluginOpen(id)` work **only for the plugin's own id**
  (pluginOwnsTarget, 388-392, 630-650).
- A third-party plugin therefore cannot call `shell.summon("omarchy.image-picker")`
  from QML. To use another plugin it shells out to `omarchy-shell` or `omarchy-menu-select`.
- `updateEntryInline(ownId, settings)` persists settings (651-656).
- `appLibrary` is set only when the manifest has kind `menu` (606-607). It is the
  desktop-app list: `sortedEntries(query)`, `iconSource`, `launch`, `remove`
  (`services/PluginAppLibraryApi.qml`).

## 3. What a menu plugin can render

There is no declarative row schema. The menu entry is free QML, so the plugin can do
anything Quickshell/QtQuick can. Evidence:

- **Window**: `PanelWindow` with `WlrLayershell.layer: Overlay` and
  `keyboardFocus: Exclusive`, fullscreen scrim, centred card
  (`sorydi3.window-restore/Picker.qml:197-229`).
- **List + search**: `ListView` over a filtered JS array, with type-to-filter through
  `Util.editsFilter` / `Util.editedFilter`, plus arrow/PgUp/Home/End/Enter/Delete/Esc
  handling (Picker.qml:33-41, 231-258, 297-395). Icons come from
  `DesktopEntries.heuristicLookup` + `Quickshell.iconPath` (Picker.qml:64-77).
- **Theme tokens**: `import qs.Commons` (`Color.menu.*`, `Style.*`, `Border`) and
  `import qs.Ui` (`BorderSurface`, …) give the Omarchy menu look
  (Picker.qml:9-10, 208-219). Module list: `/usr/share/omarchy/shell/Ui/qmldir`.
- **Multi-select**: no built-in multi-select menu mode. `qs.Ui` ships `MultiSelect`, a
  searchable checkbox dropdown that takes static `options` or `optionsCommand` argv
  (JSON or newline output) and emits `changed(values)` (`Ui/MultiSelect.qml:8-55`).
  A multi-select list can also be written by hand in a plugin's own ListView.
  The first-party `omarchy.menu` `select` mode returns one row only
  (`bin/omarchy-menu-select:70-98`; `plugins/menu/Menu.qml:820-834`).
- **File picking**: no in-shell file-dialog component is used anywhere in Omarchy (a grep
  for `FileDialog`/`FolderListModel` under `/usr/share/omarchy/shell` finds nothing). The options are:
  1. `omarchy-menu-file "<label>" "<dir1:dir2>" "epub pdf mobi"`. It lists files by mtime
     through `find`, then picks one via `omarchy-menu-select`, which prints the path on stdout
     (`bin/omarchy-menu-file:1-48`). It can be run from a plugin with `Process`.
  2. Build the list in-plugin: `Process` running `find …` → a `ListView` of paths.
  3. `QtQuick.Dialogs` is installed (`/usr/lib/qt6/qml/QtQuick/Dialogs`), so a
     `FileDialog` should import. Unverified: Omarchy does not use it, and a portal or
     native dialog from a layer-shell overlay has not been tested.
  4. The first-party `omarchy.image-picker` overlay shows image grids (image files only),
     driven by `omarchy-shell image-selector open …` (`plugins/README.md:52-77`).

### The first-party Omarchy menu (`omarchy.menu`), for comparison
The Omarchy menu has three modes: route `menu`, `select` and `input`
(`plugins/menu/Menu.qml:22-31, 56-61`). Scripts use the latter two over a
file-based round-trip: a payload with `selectionFile`/`doneFile` goes in, and the script polls
for `doneFile` (`bin/omarchy-menu-select:70-98`). Rows can have a glyph, label and subtext
(`omarchy-menu-select:9-13`). This dmenu-style path needs no plugin at all.

## 4. How a service runs processes and notifies

- **Long-running / streaming**: `Process { command: [...]; running: true;
  stdout: SplitParser { onRead: ... }; onExited: ... }`. window-restore wraps
  its follower in `setpriv --pdeathsig TERM` so it dies with the shell, and restarts it
  with `Timer`s (`window-restore/Service.qml:56-86`).
- **One-shot with collected output**: `Process` + `StdioCollector`, with the result read in
  `onExited(exitCode)`. If `running` goes false without `onStarted` having fired, the
  binary is missing (`Picker.qml:143-181`). Set `command` before `running = true` to pass
  arguments (Picker.qml:129-132).
- **Fire-and-forget**: `Quickshell.execDetached([argv])` (Picker.qml:121). Commons
  helpers: `Util.execArgv(argv)` runs the argv through `bash -lc 'exec "$@"'` so session PATH and env
  apply and the args stay literal, which is the right choice for filenames. `Util.execDetached(cmdString)`
  runs `bash -lc` on a string (`Commons/Util.qml:49-64`).
- **Files**: `FileView` reads, watches and atomically writes files
  (key-promoter `Service.qml:231-247`).
- **Notifications**: the shell's notification *server* is the first-party
  `omarchy.notifications` service. Its IPC target `notifications` only controls DND and
  history (`plugins/notifications/Service.qml:857-900`), and no plugin API sends one. Plugins
  send through a CLI: `omarchy-notification-send [-u …] [-g glyph] [-t ms] [--image p]
  <headline> [description] [--exec prog args…]` (`bin/omarchy-notification-send:3-4`),
  or `notify-send`. window-restore has its own CLI send it (`--notify`, Picker.qml:121).
  key-promoter draws its own toast `PanelWindow` (`Toast.qml`, `Service.qml:249-255`).

## 5. Config and settings

- `~/.config/omarchy/shell.json` is the only config file. Settings go inline on the
  plugin's entry: `plugins: [{ "id": "me.plugin", "key": value }]`, with no `config:`
  sub-object and no separate settings file (README.md:217-286, rules 2-3).
- A third-party plugin counts as enabled when its id is present in shell.json. `omarchy plugin enable <id>`
  appends `{id}` to `plugins[]` (README.md:272-276; PluginRegistry.qml:541-542).
- The shell does not inject a non-bar plugin's settings. Read them yourself:
  key-promoter reads `shell.json` with `FileView { watchChanges: true }` and picks its entry
  out of `plugins[]` (`fkcodes.key-promoter/Service.qml:44-51, 76-88, 231-238`).
- Writing: `shell.updateEntryInline(ownId, {…})` replaces the entry's fields and
  persists (`shell.qml:1081-1120`, scoped at 651-656). Shell-side bash helpers live in
  `bin/omarchy-shell-config` (sourced, then `omarchy-shell shell reloadConfig`).
- Private state outside the shell config is ordinary files, e.g. key-promoter's
  `~/.local/state/omarchy/key-promoter.json` (Service.qml:42, 240-247).
- `barWidget.schema`/`defaults` give bar widgets a settings UI. Menu and service kinds
  have no equivalent (README.md:61-70).

## 6. Opening a plugin menu

- **CLI / IPC**: `omarchy-shell shell toggle <id> '<payloadJson>'` (or `summon`, `hide`).
  A missing payload defaults to `{}` (`bin/omarchy-shell:51-53`). It returns
  `unknown` if the plugin is unknown or disabled (`shell.qml:1155-1169, 1718-1728`).
- **Hyprland bind** (Lua bindings on this machine):
  `o.bind("SUPER + ALT + Z", "Pick a closed window (Omarchy)", "omarchy-shell shell toggle sorydi3.window-restore")`
  (`~/.config/hypr/bindings.lua:44`). Default binds use the same pattern, e.g.
  `/usr/share/omarchy/default/hypr/bindings/clipboard.lua:48`.
- **Omarchy menu entry**: add a row to `~/.config/omarchy/extensions/omarchy-menu.jsonc`
  whose `action` is that command, e.g.
  `"kindle": {"icon":"…","label":"Send to Kindle","action":"omarchy-shell shell toggle me.kindle-send"}`.
  Supported fields are `icon`, `label`, `action`, `target`, `provider`, `aliases`,
  `description`, `when` and `checked` (omarchy-menu.jsonc:8-17). The file is watched (`plugins/README.md:110-115`).
  `provider` names are hard-coded in Menu.qml (`fonts`, `power-profiles`, apps), so
  third parties cannot add dynamic rows that way (`plugins/menu/Menu.qml:265-282`).
- **From its own bar widget**: `bar.shell.toggle(ownId, "{}")`
  (`window-restore/Widget.qml:34-36`).

## 7. Triggering a plugin from outside the shell (e.g. a Nautilus script)

Yes. Every route is `qs ipc` against the running shell, wrapped by
`/usr/share/omarchy/bin/omarchy-shell` (`qs ipc -n -p $OMARCHY_PATH/shell call -- "$@"`,
line 59). The wrapper needs `OMARCHY_PATH` set (line 40). It recovers `WAYLAND_DISPLAY`
from the runtime dir when that is unset (46-49), so a Nautilus script running inside
the session works. Failures are reported as "not running" / "Target not found." (62-77).

1. **Open the menu with data**: `omarchy-shell shell summon me.kindle-send '{"files":["/a.epub","/b.pdf"]}'`.
   The JSON string arrives in the menu's `open(payloadJson)` (shell.qml:1183-1191, 1261-1263).
   This is the cleanest way for a Nautilus script to hand over selected files
   (`$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS`).
2. **Call a method on a loaded menu/panel item**: `omarchy-shell shell call <id> <method> <arg>`.
   It returns the method's string result, or `ok`, `unknown` or `error` (shell.qml:1282-1294, 1743-1745).
   It only reaches **menu/panel/overlay** loader items, not services (it looks up
   `panelLoaders`), and the item must be loaded (summoned, or `keepLoaded: true`).
3. **Own IPC target**: put `IpcHandler { target: "kindle-send"; function send(path: string): string {…} }`
   in the service, then call `omarchy-shell kindle-send send /path`. A third-party
   service doing this already works on this machine:
   `fkcodes.key-promoter/Service.qml:257-281`, used as
   `omarchy-shell key-promoter show …` (its README.md:99-104). IPC arguments are strings only
   (README.md:212-215). Several files would need a JSON or newline-joined string.

Caveat: anything outside the shell can also just run the plugin's CLI directly.
window-restore keeps its logic in a separate `window-restore` program and treats the
plugin as a thin UI over it, so binds work even when the shell is down
(`~/.config/hypr/bindings.lua:33-39`).

## Open / unverified

- Whether `QtQuick.Dialogs.FileDialog` works from a layer-shell plugin. It is installed but
  untested here.
- IPC target names are global. A plugin's `IpcHandler` target must not clash with
  existing ones (`shell`, `image-selector`, `notifications`, `media`, …; grep `IpcHandler`
  under `/usr/share/omarchy/shell`).
