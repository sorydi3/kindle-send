# What can an omarchy-shell menu and service plugin do?

Type: research
Status: resolved
Blocked by: none
Parent: ../map.md

## Question

From `/usr/share/omarchy/shell` (README, plugin loader, services) and the existing plugins in `~/.config/omarchy/plugins/` (especially `sorydi3.window-restore`): what can a `menu` plugin show (lists, search, file picking?), how a `service` runs external processes and sends notifications, how plugins store config and settings, how a plugin is opened from a keybinding or the Omarchy menu, and whether something outside the shell (e.g. a Nautilus script) can trigger a plugin action (IPC or a command).

## Answer

Full findings with file and line citations: branch `research/plugin-api`, file `research/plugin-api.md` (commit f424b34; never merged).

- Manifest needs `schemaVersion`, `id`, `name`, `version`, `kinds`, `entryPoints`; one plugin can combine `menu` + `service`.
- A menu is free-form QML: the shell calls `open(payloadJson)` / `close()`; the plugin draws its own window, list and search (window-restore's `Picker.qml` is a full example). No built-in file picker or multi-select (`qs.Ui` has a `MultiSelect`; `omarchy-menu-file` exists as a helper).
- A service runs programs with Quickshell `Process`; no notification API, so use `notify-send` / `omarchy-notification-send`.
- Settings live inline on the plugin's entry in `~/.config/omarchy/shell.json` `plugins[]`; the plugin reads that file itself and writes with `shell.updateEntryInline`.
- Open the menu with `omarchy-shell shell toggle <id> '<json>'` from a Hyprland bind or an `omarchy-menu.jsonc` action.
- From outside the shell: `omarchy-shell shell summon <id> '{"files":[...]}'` delivers a payload to the menu; a service can register an `IpcHandler` callable as `omarchy-shell <target> <fn> args` (string args only).
