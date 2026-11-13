# Settings live in their own file, not in shell.json

Settings move from the plugin's entry in `~/.config/omarchy/shell.json` to `~/.config/kindle-send/settings.json` (`$XDG_CONFIG_HOME`, mode 600), written only by `kindle-send`. Omarchy deletes a plugin's `plugins[]` entry when the plugin is disabled or removed, so Settings kept there were lost on a disable/enable, and writing that entry also enables a third-party plugin, so saving Settings could quietly re-enable a disabled one. Omarchy's own convention is inline settings in `shell.json`; we leave it for these two reasons.

## Consequences

- The first time `kindle-send` finds no `settings.json` but finds Settings in the old `shell.json` entry, it copies them over once; it never writes `shell.json` again.
- Settings, the keyring password and the Send history all survive `omarchy plugin remove`; the README's Remove section lists how to delete them.
- The Send limit numbers move with the other Settings.
