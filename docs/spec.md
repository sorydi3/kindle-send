# Send to Kindle: spec

An omarchy-shell plugin that sends ebooks on this machine to the user's Kindle, by email (through Gmail) or over USB.

- Status: ready to build. Every decision below comes from the wayfinder map, [issue #1](https://github.com/sorydi3/kindle-send/issues/1). Each section links the ticket that holds the full reasoning.
- Vocabulary (Book, Route, Send, Pending Send, Email limit, Conversion, Book folders, Send limit, Send history): see [`GLOSSARY.md`](../GLOSSARY.md).
- Sections marked **Proposed** were not decided in a ticket. They fill gaps between decisions and may change during the build without reopening the map.

## 1. Scope

**In scope**

- Local Books only: files already on disk.
- One Kindle address.
- Two Routes: Email (Gmail SMTP with an app password) and USB (drive-style Kindles).
- Three ways in: a picker opened by `SUPER + SHIFT + K` or the Omarchy menu; a Nautilus right-click entry; the `kindle-send` command.
- Built for one user (the author). No personal details or secrets in the code.

**Out of scope**

- Web articles, or finding and downloading books.
- More than one Kindle address.
- Formats neither Route accepts: CBZ/CBR, FB2, DjVu, LIT ([#7](https://github.com/sorydi3/kindle-send/issues/7)).
- MTP Kindles (2024+ models, Scribe) ([#13](https://github.com/sorydi3/kindle-send/issues/13)).
- Publishing for other Omarchy users (kept possible, not done).
- Amazon's "Send to Kindle for Web" (no API) and USB over MTP.

**Target machine** (verified 2026-11-04): Omarchy with omarchy-shell plugins, Nautilus 51 with `nautilus-python` 4.2, `udiskie --automount` running, GNOME Keyring running as the Secret Service, `python3`. The Kindle is a Paperwhite 5 (2021), firmware 5.19.2, USB id `1949:0324`, mass storage ([#12](https://github.com/sorydi3/kindle-send/issues/12)).

## 2. Components

```
plugin/            omarchy-shell plugin  sorydi3.kindle-send  (kinds: menu + service)
  manifest.json
  Picker.qml       the menu: lists Books, marks, Route override, opens setup
  Service.qml      background: runs Sends, queues, notifications, Kindle detection
bin/kindle-send    Python 3, standard library only: does the actual work
nautilus/kindle-send.py   nautilus-python extension: right-click "Send to Kindle"
assets/test.epub   tiny EPUB for the setup test send
scripts/install.sh, scripts/uninstall.sh
```

Who does what:

| Piece | Responsibilities |
|---|---|
| **Picker** (QML) | Show Books, marks and Routes; keys; closes on send and hands the Send to the Service. Never sees the password. |
| **Service** (QML) | Owns everything held in memory: the Send queue, Pending Sends, Books held by the Send limit. Runs `kindle-send` per Book, polls for the Kindle while something is pending, posts and updates notifications. |
| **`kindle-send`** (Python) | Reads settings and the keyring itself. Classifies Books, picks Routes, converts, emails, copies, ejects, writes the Send history, runs setup and prints history. Testable without the shell. |
| **Nautilus extension** | Adds the right-click item for supported files; summons the Picker with those files. |

Plugin manifest (shape per [#4](https://github.com/sorydi3/kindle-send/issues/4)):

```json
{
  "schemaVersion": 1,
  "id": "sorydi3.kindle-send",
  "name": "Send to Kindle",
  "version": "0.1.0",
  "description": "Send ebooks to your Kindle by email or USB",
  "kinds": ["menu", "service"],
  "keepLoaded": true,
  "entryPoints": { "menu": "Picker.qml", "service": "Service.qml" }
}
```

## 3. `kindle-send` command interface (Proposed)

All subcommands that the Service calls print **one JSON object per line** on stdout, so QML can read them line by line (Quickshell `Process` + `SplitParser`). Exit code 0 means the command ran; per-Book results are in the JSON.

| Command | Purpose |
|---|---|
| `kindle-send plan [--folders] [FILE...]` | Classify Books for the Picker. With `--folders`, scan the Book folders; with files, classify just those. One line per Book: `{"path","name","format","size","mtime","route","routeReason","emailOk","usbOk","lastSent"}`. Unsupported files are left out. If any setting or the app password is missing, the first line is `{"setupNeeded": true, "missing": [...]}` (`"appPassword"` for the password; the password itself is never printed). |
| `kindle-send send --route email\|usb FILE` | Send **one** Book by the given Route. Progress lines `{"stage": "converting"\|"sending"\|"copying"}` then one result line `{"result": "sent"\|"copied"\|"failed", "reason"?: "...", "fixBySetup"?: true}`. Writes the Send history. |
| `kindle-send kindle` | Kindle detection: `{"present": true, "mount": "...", "free": N}` or `{"present": false}`. |
| `kindle-send eject` | Unmount and power off the Kindle: `{"ejected": true}` or `{"ejected": false, "reason": "..."}`. |
| `kindle-send limit` | Send limit state from the Send history: `{"canSendIn": seconds, "sentLastHour": N, "maxEmailsPerHour": N}` (only `sent` email entries count; `maxEmailsPerHour` tells the Service whether a wait is the gap or the hourly cap). |
| `kindle-send setup` | Interactive wizard (Section 9). Needs a TTY. |
| `kindle-send history` | Prints the last 20 Sends, human-readable. |
| `kindle-send formats` | The supported formats (Section 5), lowercase without the dot: `{"formats": ["azw", ...]}`. The one list; the Nautilus extension reads it instead of keeping its own. |

The Service keeps the ordering: it decides which Book goes next, waits for `limit`, and calls `eject` once after the last USB Book of a Send.

## 4. Choosing a Book

### Picker ([#8](https://github.com/sorydi3/kindle-send/issues/8))

- **Opened by** `SUPER + SHIFT + K` (`omarchy-shell shell toggle sorydi3.kindle-send`) or the Omarchy menu entry "Send to Kindle".
- **Lists** supported Books from the Book folders (default `~/Books`, `~/Downloads`; editable), up to 3 levels deep, skipping hidden folders. Newest file first.
- **Typing** filters by file name.
- **Each row** shows name, format, size and Route (Email or USB), plus "sent N days ago" if the Send history has the same name and size ([#16](https://github.com/sorydi3/kindle-send/issues/16)). A Book the chosen Route can't take is dimmed.
- **Keys:**

  | Key | Action |
  |---|---|
  | `Space` | mark / unmark the highlighted Book |
  | `Tab` | switch the highlighted Book between Email and USB |
  | `Enter` | send the marked Books, or the highlighted one if none are marked; the picker closes at once |
  | `Delete` | on the "N Books waiting for Kindle" line: cancel those Pending Sends |
  | `Esc` | close |

- **Empty:** "No Books found in ~/Books, ~/Downloads", with a hint that folders can be changed in settings (rerun setup).
- **Setup needed:** if a setting is missing, the picker shows only "Set up Send to Kindle"; `Enter` launches the setup wizard ([#14](https://github.com/sorydi3/kindle-send/issues/14)).
- **Pending Sends:** if any exist, a "N Books waiting for Kindle" line sits at the top ([#15](https://github.com/sorydi3/kindle-send/issues/15)).
- No "browse elsewhere" option.

### Nautilus right-click ([#10](https://github.com/sorydi3/kindle-send/issues/10))

- A `nautilus-python` extension (modelled on `~/.local/share/nautilus-python/extensions/localsend.py`) adds a top-level **"Send to Kindle"** item.
- It appears only when at least one selected item is a file with a supported extension. Folders never get it.
- It runs `omarchy-shell shell summon sorydi3.kindle-send '{"files": [...]}'` with the supported files. The Picker opens listing **only those files, already marked**; Routes and `Tab` work as usual.
- Unsupported files in a mixed selection are left out, and a notification lists them.
- The extension asks `kindle-send formats` once per Nautilus process for the supported extensions, so the format list lives only in `kindle-send`. Without `kindle-send` on `PATH` there is no item. Commands are argv lists, never a shell, so names with spaces or non-ASCII characters pass through unchanged.

## 5. Routes ([#6](https://github.com/sorydi3/kindle-send/issues/6), [#7](https://github.com/sorydi3/kindle-send/issues/7))

Supported formats:

| Format | Email | USB |
|---|---|---|
| EPUB | yes (Amazon converts) | after Conversion to AZW3 (needs Calibre) |
| PDF | yes, sent unchanged, no "convert" subject | yes |
| TXT | yes | yes |
| DOC, DOCX, RTF, HTML/HTM, JPG/JPEG, PNG, GIF, BMP | yes | refused |
| AZW3, AZW, MOBI, PRC, KFX | no | yes |

Route rules, per Book:

1. **Automatic:** Email if the format is accepted by email **and** the Book fits the Email limit; otherwise USB.
2. **Email wins** when both work, even with the Kindle plugged in.
3. **Override:** `Tab` in the Picker. A Book the chosen Route can't take fails with its reason; it never switches Route on its own.
4. **Per Book:** one Send can use both Routes.
5. **No fallback:** a failed email is reported, not retried over USB.

**Email limit (Proposed estimate):** Gmail's server advertises its maximum message size (35,882,577 bytes when measured, after base64 encoding). `plan` estimates the raw-file limit as `(advertised − 64 KiB) / 1.37` and caches the last advertised value in `~/.local/state/kindle-send/` (default 35,882,577 until the first send). `send` reads the real value from the server; if the Book is too big, it fails with "Too big for email, switch it to USB."

## 6. Email route ([#5](https://github.com/sorydi3/kindle-send/issues/5), [#11](https://github.com/sorydi3/kindle-send/issues/11))

- Python `smtplib.SMTP_SSL("smtp.gmail.com", 465)`; login with `senderAddress` and the app password from the keyring.
- **One email per Book:** From `senderAddress`, To `kindleAddress`, subject = file name without extension, a one-line body, the Book attached with its MIME type (`application/epub+zip` for EPUB).
- Success means **Gmail accepted the message**. Amazon sends nothing back, neither on success nor on failure (verified live), so the plugin can never confirm delivery.
- An unapproved sender fails silently. Setup's test send is the only check.

## 7. USB route ([#13](https://github.com/sorydi3/kindle-send/issues/13))

- **Detection:** find a mounted block device whose USB vendor id is `1949` (e.g. `lsblk -J -o NAME,MOUNTPOINTS,...` plus `udevadm info` for `ID_VENDOR_ID`, or udisks); use its mount point. Never hard-code `/run/media/...`. Mass storage only.
- **No Kindle:** the Book becomes a **Pending Send**, held by the Service. The Service runs `kindle-send kindle` every 3 s (Proposed) while anything is pending and stops when nothing is. When the Kindle appears, pending Books go out.
- **Copy**, for each Book:
  1. Convert if it's an EPUB (Section 8).
  2. Check free space; fail if there isn't enough.
  3. Copy to `documents/.<name>.part`, rename to `documents/<name>` (replacing a same-name file), then `fsync`.
- **Eject** once after the last USB Book of a Send: `udisksctl unmount -b <partition>` then `udisksctl power-off -b <device>`. If it fails (e.g. Nautilus has the drive open), the Books stay copied and the notification asks the user to eject.
- After an eject, a later USB Send needs the Kindle plugged back in, so it becomes a Pending Send.

## 8. Conversion ([#7](https://github.com/sorydi3/kindle-send/issues/7))

- Only EPUB, only on the USB Route: `ebook-convert <book>.epub <tmpdir>/<name>.azw3`.
- Calibre is optional. If `ebook-convert` is missing, that Book fails: "Install calibre to send EPUB over USB (`sudo pacman -S calibre`)."
- The AZW3 lives in a temp folder and is deleted after copying. The original is never changed.
- A failed Conversion is reported like any other failure.

## 9. Settings, secrets and setup ([#9](https://github.com/sorydi3/kindle-send/issues/9), [#14](https://github.com/sorydi3/kindle-send/issues/14))

**Settings** live inline on the plugin's entry in `~/.config/omarchy/shell.json` (mode 600):

```json
{ "id": "sorydi3.kindle-send",
  "kindleAddress": "…@kindle.com",
  "senderAddress": "…@gmail.com",
  "bookFolders": ["~/Books", "~/Downloads"],
  "minEmailGapSeconds": 10,
  "maxEmailsPerHour": 20 }
```

**App password:** GNOME Keyring, attributes `service=kindle-send user=<senderAddress>`. Read by `kindle-send` with `secret-tool lookup`. It never passes through QML or a command line. An empty stored value counts as missing.

**Missing setting or password:** the Send fails before anything is sent. The notification names what's missing, and clicking it opens setup.

**`kindle-send setup`**, run in a floating terminal (`omarchy-launch-floating-terminal-with-presentation kindle-send setup`), from the Picker or "Send to Kindle → Setup" in the Omarchy menu:

1. Kindle address, with where to find it (amazon.com → Manage Your Content and Devices → Devices).
2. Gmail address.
3. App password: shows https://myaccount.google.com/apppasswords, then runs `secret-tool store`, which prompts in the terminal.
4. "Add <Gmail> to Amazon's Approved Personal Document Email List", with the link. Waits for Enter.
5. Book folders, defaults filled in.
6. Create `~/Books` if missing.
7. Optional test send of `assets/test.epub`, then: "Did 'Kindle Send Test' appear on your Kindle within a few minutes?" On no: list the usual causes (sender not approved, wrong Kindle address).

On a rerun, current values are filled in, and `Enter` keeps each one (including the stored password). Settings are written to `shell.json` keeping all other keys intact. **Proposed:** the wizard writes the file itself, and the Service picks the change up through its `FileView`.

## 10. Feedback ([#15](https://github.com/sorydi3/kindle-send/issues/15))

All through `omarchy-notification-send` (`-p` for the id, `-r` to replace, `-u` urgency, `--exec` on click). It defaults to low urgency; only critical notifications stay on screen. There are no notification buttons (the server draws none).

- **One notification per Send, updated in place:** "Sending N Books…" → "Converting <Book>…" → "Copying to Kindle…" → summary.
- **Summary**, one line per Book (a single sentence for one Book):
  - Email: "Sent to Amazon. Should appear on your Kindle within a few minutes."
  - USB: "Copied to Kindle." plus "Kindle ejected, safe to unplug" or "Please eject the Kindle."
- **All fine:** normal urgency, disappears after a few seconds.
- **Any failure:** critical, stays until dismissed, names each failed Book with its reason. If the reason is a missing setting or a rejected password, clicking runs setup.
- **Pending Send:** a lasting (critical) notification "Waiting for Kindle: <Book>. Plug it in to send. Click to manage." Omarchy's notification server draws no buttons, so clicking it opens the Picker, where `Delete` on the waiting line cancels.
- **Send limit hold:** "Holding N Books to stay under Amazon's limit. Next in M min."

## 11. Send limit ([#15](https://github.com/sorydi3/kindle-send/issues/15), [#16](https://github.com/sorydi3/kindle-send/issues/16))

- At least `minEmailGapSeconds` (10) between emails, at most `maxEmailsPerHour` (20) emails per rolling hour. Both live in settings.
- The count comes from the Send history, so it survives shell restarts. Books held back wait in the Service's memory and are lost on a shell restart, like Pending Sends.
- The USB Route is not limited.

## 12. Send history ([#16](https://github.com/sorydi3/kindle-send/issues/16))

- `~/.local/state/kindle-send/history.jsonl`, one line per Book: `{"time","name","size","route","result","reason"?}`. Entries older than 90 days are dropped on write.
- Same Book = same file name and size.
- Failed Sends are recorded too, but only successful ones (`sent` or `copied`) mark a Book as sent (`lastSent`) or count toward the Send limit (`sent` only).
- Used only for: the Picker's "sent N days ago" mark, the Send limit count, and `kindle-send history` (last 20, newest first, local time, e.g. `Nov 4 23:17 · Dune.epub · Email · Sent to Amazon`; also `… · USB · Copied to Kindle` and `… · Email · Failed: <reason>`).
- Re-sending needs no confirmation.

## 13. Failure reasons

| Situation | Reason shown | Click opens setup |
|---|---|---|
| Setting missing | "Not set up: <setting> missing." | yes |
| App password missing or rejected | "Gmail rejected the app password." / "No app password stored." | yes |
| Too big for email | "Too big for email (N MB). Switch it to USB." | no |
| Format refused on USB | "<FORMAT> can't be read over USB. Send it by email." | no |
| EPUB over USB, no Calibre | "Install calibre to send EPUB over USB (`sudo pacman -S calibre`)." | no |
| Conversion failed | "Couldn't convert: <first line of error>." | no |
| Not enough space on Kindle | "Not enough space on the Kindle (needs N MB)." | no |
| Network or SMTP error | "Couldn't reach Gmail: <error>." | no |
| Eject failed | Books copied; "Please eject the Kindle." | no |

## 14. Install and uninstall ([#17](https://github.com/sorydi3/kindle-send/issues/17))

Modelled on `~/Projects/omarchy-window-restore/scripts/install.sh`.

`scripts/install.sh`:

1. **Check dependencies:** `python3`, `nautilus-python`, `secret-tool`, `udisksctl`. If one is missing, stop with a clear message. For Calibre, only print "Optional: `sudo pacman -S calibre` to send EPUB over USB". Never run `sudo`.
2. **Copy files:**
   - `bin/kindle-send` → `~/.local/bin/kindle-send`, plus `assets/` beside it in `~/.local/share/kindle-send/`
   - `plugin/` → `~/.local/share/kindle-send/omarchy-plugin`, symlinked as `~/.config/omarchy/plugins/sorydi3.kindle-send`
   - `nautilus/kindle-send.py` → `~/.local/share/nautilus-python/extensions/`
3. **Edit config, after asking for each edit, each backed up first and wrapped in `>>> kindle-send … >>>` / `<<< kindle-send <<<` markers:**
   - `~/.config/hypr/bindings.lua`: `SUPER + SHIFT + K` → `omarchy-shell shell toggle sorydi3.kindle-send`
   - `~/.config/omarchy/extensions/omarchy-menu.jsonc`: "Send to Kindle" (toggle the picker) and "Send to Kindle → Setup" (floating terminal running `kindle-send setup`)
4. **Enable and reload:** `omarchy plugin enable sorydi3.kindle-send` (it has no bar widget, so nothing else enables it), `omarchy-shell -q shell rescanPlugins`, `nautilus -q`.
5. **Finish:** offer to run `kindle-send setup`.

Rerun install to update.

`scripts/uninstall.sh` removes everything install added: files, the symlink and the marker blocks. It keeps the settings in `shell.json`, the keyring password and the Send history, unless `--purge` is given.

## 15. Acceptance checks

1. Fresh install on this machine: dependency check passes, config edits are asked about, the keybinding opens the Picker, and the Picker shows "Set up Send to Kindle".
2. Setup stores settings in `shell.json` and the password in the keyring (non-empty), creates `~/Books`, and the test EPUB arrives on the Kindle.
3. A small EPUB in `~/Downloads` shows Route Email. Sending it gives "Sent to Amazon…", it appears on the Kindle, and the Picker then marks it "sent just now".
4. A PDF over the Email limit shows Route USB. With the Kindle unplugged, it becomes a Pending Send; clicking its notification opens the Picker, where `Delete` cancels. Plugging in copies it into `documents/`, ejects the Kindle, and it shows in the Kindle library.
5. An EPUB switched to USB with `Tab` fails with the Calibre message when Calibre isn't installed, and converts and copies when it is.
6. Nautilus: selecting a PDF and a CBZ and right-clicking shows "Send to Kindle". The Picker opens with just the PDF marked, and a notification lists the CBZ as unsupported. Right-clicking a folder shows no item.
7. Sending 25 small Books by email: the first 20 go out at least 10 s apart, and the rest are held with a "Next in M min" notification.
8. A wrong app password fails with a critical notification, and clicking it opens setup.
9. `kindle-send history` lists the Sends above. `uninstall.sh` removes the plugin, binding, menu entries and Nautilus item, and keeps the settings and history.

## 16. Known facts and caveats

- Amazon delivered a password-protected PDF even though its help pages say those are rejected ([#11](https://github.com/sorydi3/kindle-send/issues/11)). Not checked: whether it opens.
- DOCX by email was not tested live.
- Amazon's throttle numbers are unpublished. 10 s and 20 per hour are cautious guesses.
- Gmail app passwords need 2-Step Verification and are revoked when the Google account password changes ([#5](https://github.com/sorydi3/kindle-send/issues/5)).
- Research notes live on unmerged branches: `research/email-route`, `research/usb-route`, `research/plugin-api`, `research/smtp-secrets`.
