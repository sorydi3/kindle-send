# Map: Send to Kindle (omarchy-shell plugin)

Label: wayfinder:map

## Destination

A spec ready to build from for a native omarchy-shell plugin that sends local Books to the user's Kindle by email or USB. Everything the build needs is decided: plugin surfaces, Route choice, format handling, config and secrets, feedback, and install.

## Notes

- Domain: an omarchy-shell plugin (`manifest.json` + QML; kinds `menu`, `service`), installed into `~/.config/omarchy/plugins/`. Prior art from the same user: `sorydi3.window-restore` (symlinked from `~/.local/share/window-restore/omarchy-plugin`), `sorydi3.hello`.
- Settled during charting: surfaces are **menu + service** (no bar widget); a Nautilus right-click entry is also in scope as a thin second way in; both **Email** and **USB** Routes are in scope (USB because some Books are large); Email Route sends from the user's Gmail with an app password; one Kindle address; built for the user only, but with no personal details or secrets in the code.
- Vocabulary: see `GLOSSARY.md`. Skills to consult: `grilling` + `domain-modeling` for grilling tickets; the `omarchy` skill for anything touching Omarchy config.
- Tracker: local markdown. Tickets in `.scratch/kindle-send/issues/`, with `Type:`, `Status:` (open/claimed/resolved) and `Blocked by:` lines.

## Decisions so far

<!-- one line per resolved ticket: [title](issues/NN-slug.md): gist -->

- [What can an omarchy-shell menu and service plugin do?](issues/03-plugin-api-facts.md): menu is free-form QML opened with a JSON payload; service runs processes and notifies via `notify-send`; settings live in `shell.json`; outside callers use `omarchy-shell shell summon` or a service `IpcHandler`.
- [How can a script send Gmail mail and keep the app password safe on this machine?](issues/04-smtp-and-secrets-facts.md): Python `smtplib` over `smtp.gmail.com`; raw attachment ceiling about 25 MiB; app password in the already-running gnome-keyring via `secret-tool`, read by the send script, not QML.

## Not yet specified

- **Feedback and failure handling**: what the user sees while a Send runs and after it. The Email route can fail silently (Amazon rejects by replying to the sender), so what "success" means needs thought once the Routes are understood.
- **First-run setup**: how the Kindle address, Gmail account and app password get entered the first time.
- **Send history**: whether to remember what was sent, and whether that's useful at all.
- **Install and layout**: where the source lives, and how it's linked into the plugins folder (likely like window-restore).

## Out of scope

- Web articles, or finding and downloading books: only local Books.
- More than one Kindle address.
- Publishing the plugin for other Omarchy users (code stays free of personal details so this stays possible later).
- Building the plugin: this map ends at the spec.
