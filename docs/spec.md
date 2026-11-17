# Books to Kindle: spec

An omarchy-shell plugin, **Books to Kindle** (id `sorydi3.kindle-send`), that sends ebooks on this machine to the user's Kindle, by email (through Gmail) or over USB. Unofficial: not created or endorsed by Amazon.

- Status: ready to build. Every decision below comes from the wayfinder map, [issue #1](https://github.com/sorydi3/kindle-send/issues/1), for Settings in the Picker, the map [issue #29](https://github.com/sorydi3/kindle-send/issues/29), and for publishing, the map [issue #46](https://github.com/sorydi3/kindle-send/issues/46) (Section 17). Each section links the ticket that holds the full reasoning.
- Vocabulary (Book, Route, Send, Pending Send, Email limit, Conversion, Book folders, Send limit, Send history, Settings, Setup): see [`GLOSSARY.md`](../GLOSSARY.md).
- Sections marked **Proposed** were not decided in a ticket. They fill gaps between decisions and may change during the build without reopening the map.

## 1. Scope

**In scope**

- Local Books only: files already on disk.
- One Kindle address.
- Two Routes: Email (Gmail SMTP with an app password) and USB (drive-style Kindles).
- Ways in: the bar widget; a picker opened by `SUPER + SHIFT + K` or the Omarchy menu (optional extras); a right-click entry in Nautilus or Strata (optional extras); the `kindle-send` command.
- Published for any Omarchy user through `omarchy plugin add` and plugins.omarchy.org (Section 17). Built and tested on the author's machine, but designed for any Omarchy user: first-run, setup and failure messages must make sense to a stranger, and nothing may assume the author's machine, Kindle model or folders. No personal details or secrets in the code.

**Out of scope**

- Web articles, or finding and downloading books.
- More than one Kindle address.
- Formats neither Route accepts: CBZ/CBR, FB2, DjVu, LIT ([#7](https://github.com/sorydi3/kindle-send/issues/7)).
- MTP Kindles (2024+ models, Scribe) ([#13](https://github.com/sorydi3/kindle-send/issues/13)).
- An AUR or other system package; translations beyond the English catalog; support promises (response times, compatibility guarantees).
- Amazon's "Send to Kindle for Web" (no API) and USB over MTP.

**Target machine** (verified 2026-11-04): Omarchy with omarchy-shell plugins, Nautilus 51 with `nautilus-python` 4.2, `udiskie --automount` running, GNOME Keyring running as the Secret Service, `python3`. The Kindle is a Paperwhite 5 (2021), firmware 5.19.2, USB id `1949:0324`, mass storage ([#12](https://github.com/sorydi3/kindle-send/issues/12)).

## 2. Components

The repo root is the plugin (Section 17), so `omarchy plugin add` installs all of it:

```
manifest.json      omarchy-shell plugin  sorydi3.kindle-send  (kinds: menu + service + bar-widget)
Picker.qml         the menu: lists Books, marks, Route override, Settings
Service.qml        background: runs Sends, queues, notifications, Kindle detection
BarWidget.qml      the bar icon: opens the Picker, shows the waiting count
*.js               pure decision logic (rows, settings form, feedback, …), tested under node
i18n/en.json       the plugin's own text (Section 17)
bin/kindle-send    Python 3, standard library only: does the actual work; bundled, called by its path in the plugin folder
assets/test.epub   tiny EPUB for the test send
nautilus/kindle-send.py   nautilus-python extension: right-click "Send to Kindle" (optional extra)
scripts/strata_action.py  writes Strata's right-click "Send to Kindle" action (optional extra)
scripts/install.sh the optional extras script, with --remove and --purge (Section 14)
README.md, LICENSE, preview.png, tests/, docs/
```

Who does what:

| Piece | Responsibilities |
|---|---|
| **Picker** (QML) | Show Books, marks and Routes; keys; closes on send and hands the Send to the Service. Shows the Settings form (Section 9). Sees the app password only while it is typed into Settings' masked field, hands it to `kindle-send save` on stdin and forgets it ([ADR 0001](adr/0001-picker-takes-the-app-password.md)). |
| **Bar widget** (QML) | A book icon; click opens the Picker; shows the count of Books waiting for the Kindle plus emails held, when not zero; highlighted while a Send runs; tooltip with the state (Section 17). |
| **Service** (QML) | Owns everything held in memory: the Send queue, Pending Sends, Books held by the Send limit. Runs `kindle-send` per Book, polls for the Kindle while something is pending, posts and updates notifications. |
| **`kindle-send`** (Python) | Reads settings and the keyring itself. Classifies Books, picks Routes, converts, emails, copies, ejects, writes the Send history, validates and saves Settings (the only writer of the Settings file and the keyring entry), runs the terminal setup and prints history. Testable without the shell. |
| **Nautilus extension**, **Strata action** | Add the right-click item for supported files; summon the Picker with those files. |

Plugin manifest (shape per [#4](https://github.com/sorydi3/kindle-send/issues/4)):

```json
{
  "schemaVersion": 1,
  "id": "sorydi3.kindle-send",
  "name": "Books to Kindle",
  "version": "1.0.0",
  "author": "sorydi3",
  "license": "MIT",
  "description": "Unofficial: send ebooks to your Kindle by email or USB. Not created or endorsed by Amazon.",
  "kinds": ["menu", "service", "bar-widget"],
  "keepLoaded": true,
  "entryPoints": { "menu": "Picker.qml", "service": "Service.qml", "barWidget": "BarWidget.qml" },
  "barWidget": { "displayName": "Books to Kindle", "description": "Opens the Picker; shows Books waiting for the Kindle", "allowMultiple": false }
}
```

## 3. `kindle-send` command interface (Proposed)

All subcommands that the Service calls print **one JSON object per line** on stdout, so QML can read them line by line (Quickshell `Process` + `SplitParser`). Exit code 0 means the command ran; per-Book results are in the JSON.

| Command | Purpose |
|---|---|
| `kindle-send plan [--folders] [FILE...]` | Classify Books for the Picker. With `--folders`, scan the Book folders; with files, classify just those. One line per Book: `{"path","name","format","size","mtime","route","routeReason","routeReasonCode","routeReasonValues","emailOk","usbOk","lastSent"}` (`route` is the Route id, `email` or `usb`; the Picker names Routes itself; the reason's code is `""` for Email). Unsupported files are left out. If any setting or the app password is missing, the first line is `{"setupNeeded": true, "missing": [...]}` (`"appPassword"` for the password; the password itself is never printed). Before the Books comes `{"bookFolders": [...]}`: the Book folders as set (`~` unexpanded, defaults if unset), so the Picker keeps no default of its own. |
| `kindle-send send --route email\|usb FILE` | Send **one** Book by the given Route. Progress lines `{"stage": "converting"\|"sending"\|"copying"}` then one result line `{"result": "sent"\|"copied"\|"failed", "code"?: "...", "values"?: {...}, "reason"?: "...", "fixBySetup"?: true, "field"?: "..."}` (a failure has all three of `code`, `values`, `reason`); `fixBySetup` means the fix is in Settings, `field` names which one (`kindleAddress`, `senderAddress`, `appPassword`). With `--test` instead of FILE: emails `assets/test.epub` as "Kindle Send Test" (Section 9). Writes the Send history. |
| `kindle-send kindle` | Kindle detection: `{"present": true, "mount": "...", "free": N}` or `{"present": false}`. |
| `kindle-send eject` | Unmount and power off the Kindle: `{"ejected": true}` or `{"ejected": false, "code": "...", "values": {...}, "reason": "..."}`. |
| `kindle-send limit` | Send limit state from the Send history: `{"canSendIn": seconds, "sentLastHour": N, "maxEmailsPerHour": N}` (only `sent` email entries count; `maxEmailsPerHour` tells the Service whether a wait is the gap or the hourly cap). |
| `kindle-send settings` | The Settings for the form: `{"kindleAddress","senderAddress","bookFolders","appPasswordStored","missing"}` (`bookFolders` as written, `~` unexpanded, defaults if unset; `missing`: what setup still needs, in form order, `"appPassword"` for the password). The password itself is never printed. |
| `kindle-send save` | Reads one JSON object, on one line, on stdin: `{"kindleAddress","senderAddress","bookFolders","appPassword"?}` (`appPassword` only when one was typed). Checks the values and, when the Gmail address or app password changed, signs in to Gmail without sending (Section 9). Saves only if nothing blocks: writes the Settings file, stores the password in the keyring, creates `~/Books` on the first save. Prints `{"saved": bool, "firstSave"?: true, "problems": [{"field", "code", "values", "message", "blocking": bool, "needed"?: true}]}`; `firstSave` marks the save that completed setup; `needed` marks a missing value (the app password counts when none is typed or stored for the Gmail address). The password never appears on a command line. |
| `kindle-send setup` | Interactive terminal wizard (Section 9), the fallback to Settings in the Picker. Needs a TTY. |
| `kindle-send history` | Prints the last 20 Sends, human-readable. |
| `kindle-send formats` | The supported formats (Section 5), lowercase without the dot: `{"formats": ["azw", ...]}`. The one list; the Nautilus extension and the Strata action read it instead of keeping their own. |
| `kindle-send pick FILE...` | Summon the Picker with just the supported files among FILE, already marked; names the others on stderr. Exit 1 if none is supported. Run by the Strata action. |

The Service keeps the ordering: it decides which Book goes next, waits for `limit`, and calls `eject` once a Send has no USB Book left.

## 4. Choosing a Book

### Picker ([#8](https://github.com/sorydi3/kindle-send/issues/8))

- **Opened by** `SUPER + SHIFT + K` (`omarchy-shell shell toggle sorydi3.kindle-send`) or the Omarchy menu entry "Books to Kindle" (both optional extras), or a click on the bar widget. While setup is needed it opens straight into Settings (Section 9).
- **Lists** supported Books from the Book folders (default `~/Books`, `~/Downloads`; editable), up to 3 levels deep, skipping hidden folders. Newest file first.
- **Typing** filters by file name.
- **Each row** shows name, format, size and Route (Email or USB), plus "sent N days ago" if the Send history has the same name and size ([#16](https://github.com/sorydi3/kindle-send/issues/16)). A Book the chosen Route can't take is dimmed.
- **Keys:**

  | Key | Action |
  |---|---|
  | `Space` | mark / unmark the highlighted Book |
  | `Tab` | switch the highlighted Book between Email and USB; on a marked Book, switch every marked Book to that same Route. A switched Book's details say "switched to <Route>" |
  | `Enter` | send the marked Books, or the highlighted one if none are marked; the picker closes at once |
  | `Delete` | on the "N Books waiting for Kindle" line: cancel those Pending Sends |
  | `Up` / `Down` | move the highlight one row |
  | `PageUp` / `PageDown` | move the highlight six rows |
  | `Ctrl+,` | open Settings (Section 9). A plain comma still filters |
  | `Esc` | clear the search, or close |

- **Footer:** the keys that work on the highlighted row, with `Enter` saying what it sends ("Send this Book", "Send 3 Books"), always ending "Ctrl+,  Settings      Esc  Close". With Books marked, a status line above gives the count and any Route that can't take some of them ("3 Books marked · USB can't take 1").
- **Mouse:** click a row to mark or unmark it; double-click to send just that Book. A small cog at the right end of the search line opens Settings.
- **Empty:** "No Books found in ~/Books, ~/Downloads"; `Enter` opens Settings on the Book folders field.
- **Setup needed:** if a setting or the app password is missing, the Picker opens straight into Settings, titled "Set up Books to Kindle" ([#14](https://github.com/sorydi3/kindle-send/issues/14), [#32](https://github.com/sorydi3/kindle-send/issues/32)). The Book list is reachable once setup is saved.
- **Loading and failures:** after a short wait, "Looking for Books…". If listing fails or takes over 10 seconds, the picker says how to see why (`kindle-send plan --folders` in a terminal) and `Enter` tries again.
- **Pending Sends:** if any exist, a "N Books waiting for Kindle" line sits at the top ([#15](https://github.com/sorydi3/kindle-send/issues/15)).
- No "browse elsewhere" option.

### Nautilus right-click ([#10](https://github.com/sorydi3/kindle-send/issues/10))

- A `nautilus-python` extension (modelled on `~/.local/share/nautilus-python/extensions/localsend.py`) adds a top-level **"Send to Kindle"** item.
- It appears only when at least one selected item is a file with a supported extension. Folders never get it.
- It runs `omarchy-shell shell summon sorydi3.kindle-send '{"files": [...]}'` with the supported files. The Picker opens listing **only those files, already marked**; Routes and `Tab` work as usual.
- Unsupported files in a mixed selection are left out, and a notification lists them.
- The extension asks `kindle-send formats` once per Nautilus process for the supported extensions, so the format list lives only in `kindle-send`. Without `kindle-send` on `PATH` there is no item. Commands are argv lists, never a shell, so names with spaces or non-ASCII characters pass through unchanged.

### Strata right-click

[Strata](https://github.com/lgse/strata) has its own custom actions instead of extensions.

- If `strata` is installed, install writes `~/.config/strata/actions/kindle-send/action.toml` (folder `0700`, file `0600`, as Strata requires): a top-level **"Send to Kindle"** command action that runs `kindle-send pick {paths}` for files whose extension is in `kindle-send formats`.
- It starts **turned off**, as Strata recommends for actions written by tools; the user turns it on in Strata's Settings → Actions. Reinstalling updates it and keeps that choice. Uninstall removes it.
- Strata shows an action only when **every** selected item matches, so a mixed selection (a PDF and a CBZ) or a folder gets no item, and there is no "left out" notification.

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
- **Eject** once per Send, as soon as it has no USB Book left (emails still to go, e.g. held by the Send limit, don't keep the Kindle mounted): `udisksctl unmount -b <partition>` then `udisksctl power-off -b <device>`. If it fails (e.g. Nautilus has the drive open), the Books stay copied and the notification asks the user to eject.
- After an eject, a later USB Send needs the Kindle plugged back in, so it becomes a Pending Send.

## 8. Conversion ([#7](https://github.com/sorydi3/kindle-send/issues/7))

- Only EPUB, only on the USB Route: `ebook-convert <book>.epub <tmpdir>/<name>.azw3`.
- Calibre is optional. If `ebook-convert` is missing, that Book fails: "Install calibre to send EPUB over USB (`sudo pacman -S calibre`)."
- The AZW3 lives in a temp folder and is deleted after copying. The original is never changed.
- A failed Conversion is reported like any other failure.

## 9. Settings, secrets and setup ([#9](https://github.com/sorydi3/kindle-send/issues/9), [#14](https://github.com/sorydi3/kindle-send/issues/14), map [#29](https://github.com/sorydi3/kindle-send/issues/29))

**Settings** live in their own file, `~/.config/kindle-send/settings.json` (`$XDG_CONFIG_HOME`, mode 600), written only by `kindle-send` ([ADR 0002](adr/0002-settings-in-their-own-file.md), [#54](https://github.com/sorydi3/kindle-send/issues/54)). Omarchy deletes a plugin's `shell.json` entry on disable or remove, and writing that entry re-enables the plugin, so Settings are not kept there. The first time `kindle-send` finds no `settings.json` but finds Settings in the plugin's old `shell.json` entry, it copies them over once; it never writes `shell.json` again.

```json
{ "kindleAddress": "…@kindle.com",
  "senderAddress": "…@gmail.com",
  "bookFolders": ["~/Books", "~/Downloads"],
  "minEmailGapSeconds": 10,
  "maxEmailsPerHour": 20 }
```

The two Send limit numbers are not in the Settings form; they are changed in this file only.

**App password:** GNOME Keyring, attributes `service=kindle-send user=<senderAddress>`. Read by `kindle-send` with `secret-tool lookup`. It is typed only into the Settings form's masked field and handed to `kindle-send save` on stdin: never on a command line, in the Settings file, a log or a file the Picker writes, and the field is cleared once it is stored ([ADR 0001](adr/0001-picker-takes-the-app-password.md)). The terminal wizard keeps `secret-tool store`'s own prompt. An empty stored value counts as missing.

**Missing setting or password:** the Send fails before anything is sent. The notification names what's missing, and clicking it opens the Picker in Settings on that field.

**One writer:** `kindle-send` is the only program that writes Settings (`kindle-send save` for the form, the wizard in a terminal). It writes the whole Settings file atomically (temp file, then rename), mode 600.

### Settings in the Picker ([#30](https://github.com/sorydi3/kindle-send/issues/30) to [#35](https://github.com/sorydi3/kindle-send/issues/35))

Settings replace the Book list inside the Picker card. They open with `Ctrl+,` or the cog, and on their own while setup is needed. One form serves both setup and later changes: titled "Set up Books to Kindle" while something is missing, "Settings" otherwise. Its values come from `kindle-send settings`.

| Field | Help line under it | `Ctrl+O` opens |
|---|---|---|
| Kindle address | "Find it at amazon.com → Manage Your Content and Devices → Devices." | Amazon's Manage Your Content and Devices |
| Gmail address | "Amazon must list it as an approved sender, or it drops every Book." | Amazon's Personal Document Settings (approved list) |
| Gmail app password (masked; "Stored. Type to replace it." when one is stored) | "Create one at myaccount.google.com/apppasswords. It needs 2-Step Verification." | Google's app passwords page |
| Book folders (comma-separated) | "The folders the Picker lists, separated by commas." | — (`Ctrl+B` / "Browse…" instead) |

A missing value is flagged next to its label ("· needed", accent color). There is no confirmation step for Amazon's approved list: nothing can check it, and the test send is the real check.

| Key | Action |
|---|---|
| `Tab` / `Shift+Tab` | next / previous field |
| `Enter` | save (from any field) |
| `Ctrl+O` | open the focused field's link (the footer shows it only on such a field) |
| `Ctrl+B` | on Book folders: browse for a folder |
| `Ctrl+T` | send a test Book (only once everything is saved) |
| `Esc` | back to the Book list, discarding unsaved edits; the footer says "Esc  Back (discard changes)" once something changed. While setup is needed: close the Picker |

- **The Book list takes no keys while Settings are open**, so `Enter` can never send a Book from behind the form.
- **Links** (also by clicking the link text) open with `omarchy-launch-browser`. The Picker closes so the browser shows; unsaved values are kept, and reopening the Picker returns to Settings with them.
- **Book folders:** `~` is kept as typed. A folder whose name contains a comma can't be listed. An emptied field saves as the defaults and then shows them. **Browse** (`Ctrl+B`, or the "Browse…" button beside the field) opens the system folder chooser: Qt's `FolderDialog`, which in omarchy-shell is the native GTK chooser. The Picker steps aside while it is open, then returns to Settings with unsaved values kept and the chosen folder appended to the field (as `~/…` inside home).
- **Saving** (`Enter`) checks values then, never on leaving a field; a field's flag clears as soon as it is edited. A problem replaces that field's help line in the accent color, focus jumps to the first problem, and the status line above the footer sums up ("2 values need fixing.").
  - **Blocks saving:** an empty required field ("N still needed before Books can be sent."), or something that isn't an email address.
  - **Saves with a warning:** a Kindle address not ending in `@kindle.com` ("Kindle addresses usually end in @kindle.com."), a sender not on `@gmail.com` ("Make sure this is a Google account."; Google Workspace addresses send through Gmail too), a Book folder that doesn't exist ("~/Bokos doesn't exist, so the Picker skips it."; it is never created).
  - **App password check:** when the Gmail address or app password changed, saving first signs in to Gmail without sending (with a typed app password the status line says "Checking the app password with Gmail…", otherwise "Saving…"). Rejected: nothing is saved, "Gmail rejected this app password." under the field. Gmail unreachable: saved anyway, "Couldn't reach Gmail to check the password. Saved anyway."
  - The first save creates `~/Books` if missing, then suggests the test: "Saved. Ctrl+T sends a test Book to check it all works."
- **Test send** (`Ctrl+T`): the Service sends `assets/test.epub` as "Kindle Send Test" by email like any Send (`kindle-send send --route email --test`; same notifications, a Send history entry). The Picker stays in Settings with one status line: "Sending a test Book…", then "Gmail accepted the test Book at <time>. Check your Kindle in a few minutes.", or the failure next to its field. Its success notification carries the usual causes instead of a question: "Sent to Amazon. Not on your Kindle in a few minutes? Check that <Gmail> is on Amazon's approved list and the Kindle address is right." Clicking it opens Settings.

### `kindle-send setup` (terminal fallback)

For terminal users and when the shell isn't running: `kindle-send setup` in a terminal.

1. Kindle address, with where to find it (amazon.com → Manage Your Content and Devices → Devices).
2. Gmail address.
3. App password: shows https://myaccount.google.com/apppasswords, then runs `secret-tool store`, which prompts in the terminal.
4. "Add <Gmail> to Amazon's Approved Personal Document Email List", with the link. Waits for Enter.
5. Book folders, defaults filled in.
6. Create `~/Books` if missing.
7. Optional test send of `assets/test.epub`, then: "Did 'Kindle Send Test' appear on your Kindle within a few minutes?" On no: list the usual causes (sender not approved, wrong Kindle address).

On a rerun, current values are filled in, and `Enter` keeps each one (including the stored password).

## 10. Feedback ([#15](https://github.com/sorydi3/kindle-send/issues/15))

All through `omarchy-notification-send` (`-p` for the id, `-r` to replace, `-u` urgency, `--exec` on click). It defaults to low urgency; only critical notifications stay on screen. There are no notification buttons (the server draws none).

- **One notification per Send, updated in place:** "Sending N Books…" → "Converting <Book>…" → "Copying to Kindle…" → summary.
- **Summary**, one line per Book (a single sentence for one Book):
  - Email: "Sent to Amazon. Should appear on your Kindle within a few minutes."
  - USB: "Copied to Kindle." plus "Kindle ejected, safe to unplug" or "Please eject the Kindle."
- **All fine:** normal urgency, disappears after a few seconds.
- **Any failure:** critical, stays until dismissed, names each failed Book with its reason. If the reason is a missing setting or a rejected password, clicking opens the Picker in Settings, on the field at fault with its problem shown.
- **Test send** (Section 9): its success summary reads "Sent to Amazon. Not on your Kindle in a few minutes? Check that <Gmail> is on Amazon's approved list and the Kindle address is right." Clicking it opens Settings.
- **Pending Send:** a lasting (critical) notification "Waiting for Kindle: <Book>. Plug it in to send. Click to manage." Omarchy's notification server draws no buttons, so clicking it opens the Picker, where `Delete` on the waiting line cancels.
- **Pending Send cancelled:** `Delete` in the Picker replaces the lasting notification with a passing (normal) "Cancelled N Books waiting for Kindle".
- **Send limit hold:** "Holding N Books to stay under Amazon's limit. Next in M min." A lasting (critical) notification of its own, so it never replaces another Send's progress. It stays while Books are held, is updated as the count changes, and turns into the summary of the held emails once the last has gone. The Send they came from has already shown its summary for its other Books. Short gap waits (seconds, `minEmailGapSeconds`) show no notice.

## 11. Send limit ([#15](https://github.com/sorydi3/kindle-send/issues/15), [#16](https://github.com/sorydi3/kindle-send/issues/16))

- At least `minEmailGapSeconds` (10) between emails, at most `maxEmailsPerHour` (20) emails per rolling hour. Both live in settings.
- The count comes from the Send history, so it survives shell restarts. Books held back wait in the Service's memory and are lost on a shell restart, like Pending Sends.
- The USB Route is not limited.
- Inside the gap, an email waits in its Send (a USB Book of the same Send goes first). Emails the hourly cap holds leave their Send and wait in a line of their own, sent one at a time in order. Their Send goes on with its USB Books, ejects and posts its summary; later Sends (USB-only ones, Books released by Pending Sends) start at once. A later email joins the held ones rather than overtaking them.

## 12. Send history ([#16](https://github.com/sorydi3/kindle-send/issues/16))

- `~/.local/state/kindle-send/history.jsonl`, one line per Book: `{"time","name","size","route","result","reason"?}`. Entries older than 90 days are dropped on write. A USB Book that finds no Kindle gets no line: it becomes a Pending Send and is recorded when it is copied or fails for another reason. A cancelled Pending Send leaves no line.
- Same Book = same file name and size.
- Failed Sends are recorded too, but only successful ones (`sent` or `copied`) mark a Book as sent (`lastSent`) or count toward the Send limit (`sent` only).
- Used only for: the Picker's "sent N days ago" mark, the Send limit count, and `kindle-send history` (last 20, newest first, local time, e.g. `Nov 4 23:17 · Dune.epub · Email · Sent to Amazon`; also `… · USB · Copied to Kindle` and `… · Email · Failed: <reason>`).
- Re-sending needs no confirmation.

## 13. Failure reasons

| Situation | Reason shown | Click opens Settings (on the field) |
|---|---|---|
| Setting missing | "Not set up: <setting> missing." | yes, on that setting |
| App password missing or rejected | "Gmail rejected the app password." / "No app password stored." | yes, on the app password |
| Too big for email | "Too big for email (N MB). Switch it to USB." | no |
| Format refused on USB | "<FORMAT> can't be read over USB. Send it by email." | no |
| EPUB over USB, no Calibre | "Install calibre to send EPUB over USB (`sudo pacman -S calibre`)." | no |
| Conversion failed | "Couldn't convert: <first line of error>." | no |
| Not enough space on Kindle | "Not enough space on the Kindle (needs N MB)." | no |
| Copy to the Kindle failed | "Couldn't copy to the Kindle: <error>." | no |
| Network or SMTP error | "Couldn't reach Gmail: <error>." | no |
| Eject failed | Books copied; "Please eject the Kindle." | no |

## 14. Install, extras and removal ([#17](https://github.com/sorydi3/kindle-send/issues/17), [#55](https://github.com/sorydi3/kindle-send/issues/55))

**Install** is Omarchy's own: `omarchy plugin add https://github.com/sorydi3/kindle-send --enable`. It clones the repo into `~/.config/omarchy/plugins/sorydi3.kindle-send/` and puts the bar widget on the bar, which is enough to use the plugin: the Picker opens from the widget and `kindle-send` is called from the plugin folder. Nothing else is required. **Update:** `omarchy plugin update sorydi3.kindle-send`.

**Optional extras:** `~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh`, run by hand, asks before each change and is safe to re-run:

1. **Check dependencies:** `python3` and `secret-tool` required; `nautilus-python`, Strata and Calibre optional. A missing optional one only skips its extra (for Calibre, print "Optional: `sudo pacman -S calibre` to send EPUB over USB"). Never run `sudo`.
2. **Link:** `~/.local/bin/kindle-send` → the bundled `bin/kindle-send`, so the terminal and the right-click extras find it. Without the link the right-click extras aren't installed.
3. **Right-click:** `nautilus/kindle-send.py` → `~/.local/share/nautilus-python/extensions/` if `nautilus-python` is installed; the Strata action → `~/.config/strata/actions/kindle-send/` if Strata is installed (Section 4).
4. **Edit config, each backed up first and wrapped in `>>> kindle-send … >>>` / `<<< kindle-send <<<` markers:**
   - `~/.config/hypr/bindings.lua`: `SUPER + SHIFT + K` → `omarchy-shell shell toggle sorydi3.kindle-send`
   - `~/.config/omarchy/extensions/omarchy-menu.jsonc`: "Books to Kindle" (toggle the Picker) and "Books to Kindle → Settings" (`omarchy-shell shell summon sorydi3.kindle-send '{"settings":""}'`). An older block is replaced in place (asked like any edit); an up-to-date block is left as it is.
5. **Reload:** `nautilus -q` only if the Nautilus extension changed.
6. **Finish:** say the Picker opens from the bar widget (and `SUPER + SHIFT + K` if added). On a terminal, ask "Set up in the terminal instead? [y/N]" and run `kindle-send setup` on yes.

Asking needs a terminal: without one the script makes no edits and says so. `--yes` makes them without asking. Each block goes in only once; the menu block goes before the final `}`; after an edit the script checks the file with the shell's own parsing rules and restores the backup if that fails; a menu file that already fails to parse is left alone. Backups: `<file>.before-kindle-send`.

**Remove:** `scripts/install.sh --remove` removes the extras (binding and menu blocks, the link, the Nautilus extension, the Strata action); `--purge` also deletes `~/.config/kindle-send/`, the keyring password (`secret-tool clear service kindle-send`) and the Send history (`~/.local/state/kindle-send/`). Then `omarchy plugin remove sorydi3.kindle-send` removes the plugin itself; without `--purge`, Settings, the password and the Send history survive it.

## 15. Acceptance checks

1. Fresh install with `omarchy plugin add … --enable` on a plain Omarchy: the bar widget appears, clicking it opens the Picker straight into Settings titled "Set up Books to Kindle". The extras script then asks about each extra, and `SUPER + SHIFT + K` opens the Picker.
2. Setup in the Picker's Settings stores settings in `~/.config/kindle-send/settings.json` and the password in the keyring (non-empty; never on a command line), creates `~/Books`, and `Ctrl+T` sends the test EPUB, which arrives on the Kindle. A wrong app password is refused on save with "Gmail rejected this app password."; a Book folder that doesn't exist is saved and flagged.
3. A small EPUB in `~/Downloads` shows Route Email. Sending it gives "Sent to Amazon…", it appears on the Kindle, and the Picker then marks it "sent just now".
4. A PDF over the Email limit shows Route USB. With the Kindle unplugged, it becomes a Pending Send; clicking its notification opens the Picker, where `Delete` cancels. Plugging in copies it into `documents/`, ejects the Kindle, and it shows in the Kindle library.
5. An EPUB switched to USB with `Tab` fails with the Calibre message when Calibre isn't installed, and converts and copies when it is.
6. Nautilus: selecting a PDF and a CBZ and right-clicking shows "Send to Kindle". The Picker opens with just the PDF marked, and a notification lists the CBZ as unsupported. Right-clicking a folder shows no item.
7. Sending 25 small Books by email: the first 20 go out at least 10 s apart, and the rest are held with a "Next in M min" notification.
8. A wrong app password fails with a critical notification, and clicking it opens Settings on the app password field.
9. In Settings, `Ctrl+B` opens the folder chooser and the picked folder is appended to Book folders; `Esc` after an edit discards it; `Enter` in the Book list behind Settings sends nothing.
10. `kindle-send history` lists the Sends above. `uninstall.sh` removes the plugin, binding, menu entries and Nautilus item, and keeps the settings and history.

## 16. Known facts and caveats

- Amazon delivered a password-protected PDF even though its help pages say those are rejected ([#11](https://github.com/sorydi3/kindle-send/issues/11)). Not checked: whether it opens.
- DOCX by email was not tested live.
- Amazon's throttle numbers are unpublished. 10 s and 20 per hour are cautious guesses.
- Gmail app passwords need 2-Step Verification and are revoked when the Google account password changes ([#5](https://github.com/sorydi3/kindle-send/issues/5)).
- In the folder chooser Browse opens, `Ctrl+L` (type a location) does nothing, so picking a folder there takes the mouse; typing paths into the Book folders field is the keyboard way ([#35](https://github.com/sorydi3/kindle-send/issues/35)).
- Research notes live on unmerged branches: `research/email-route`, `research/usb-route`, `research/plugin-api`, `research/smtp-secrets`.

## 17. Publishing (map [#46](https://github.com/sorydi3/kindle-send/issues/46))

Books to Kindle is published as a public git repo installed with `omarchy plugin add` and listed on plugins.omarchy.org.

### Repo and runtime ([#47](https://github.com/sorydi3/kindle-send/issues/47), [#50](https://github.com/sorydi3/kindle-send/issues/50))

- **The repo root is the plugin:** `manifest.json`, the QML and the JS sit at the root (there is no plugin subfolder); `bin/`, `assets/`, `nautilus/`, `scripts/`, `tests/` and `docs/` stay alongside and ride along into users' plugin folders (git can't exclude them; Omarchy's validator only forbids symlinks inside). `omarchy plugin validate .` must pass at the root.
- **`kindle-send` is bundled** at `bin/kindle-send` (tracked executable) and the Picker, Service and bar widget call it by its path in the plugin folder (`Qt.resolvedUrl("bin/kindle-send")` with `file://` stripped, or `manifest.__sourceDir`), never from PATH. `assets/test.epub` is found beside it.
- **Bar widget** ([#56](https://github.com/sorydi3/kindle-send/issues/56)): the `bar-widget` kind makes `omarchy plugin add --enable` enough on its own. A book icon; left-click toggles the Picker; beside it the count of Books waiting for the Kindle plus emails held by the Send limit, only when non-zero; the bar's active colour while a Send runs; tooltip "Books to Kindle" plus the state ("Sending…", "N waiting for Kindle", "N held by the Send limit", "Nothing waiting"). No right-click action. It reads its own Service through `bar.shell.serviceFor("sorydi3.kindle-send")` (`pending`, `held`, `busy`). Prototype: branch `prototype/bar-widget`.
- **Settings** in `~/.config/kindle-send/settings.json` (Section 9, ADR 0002), so disabling or removing the plugin never loses them.
- **Versions:** `1.0.0` at the first public release; minor for features, patch for fixes. `omarchy plugin update` shows users the diff.

### Translations ([#51](https://github.com/sorydi3/kindle-send/issues/51))

- The plugin's own text (Picker, Settings, footer hints, Service notifications, bar-widget tooltip, the Route labels) lives in `i18n/en.json`, read with Omarchy's `Commons.Translations`; other languages can be added later file by file. Key names (`Ctrl+,`, `Esc`, …) stay as they are. Text with a count uses plural entries (`strings.tn`); numbers and sizes go through `Commons.I18n.formatNumber`.
- `kindle-send` sends a stable `code` and its `values` with every sentence the shell shows (failure reasons in Section 13, Settings problems, Route reasons), alongside the English text, e.g. `{"code": "too_big_for_email", "values": {"mb": 76}, "reason": "Too big for email (76 MB). Switch it to USB."}`. The plugin turns the code into catalog text and falls back to the English text for a code it doesn't know. `plan` sends Route ids (`email`, `usb`), not labels. The codes, with their English text, are listed in one place: `MESSAGES` in `bin/kindle-send` (pinned by `tests/test_message_codes.py`).
- English only, by Omarchy's rule for log and diagnostic output: the Send history file, `kindle-send history`, the terminal wizard, anything printed in a terminal.

### Name, README and listing ([#48](https://github.com/sorydi3/kindle-send/issues/48), [#49](https://github.com/sorydi3/kindle-send/issues/49), [#52](https://github.com/sorydi3/kindle-send/issues/52), [#53](https://github.com/sorydi3/kindle-send/issues/53))

- **Name:** "Books to Kindle" everywhere it is shown (manifest `name`, Picker titles, notifications' app name, menu entries, bar-widget tooltip, README). "Send to Kindle" is Amazon's product name and already a listed plugin's name. The id `sorydi3.kindle-send` and the `kindle-send` command stay. The right-click item keeps its action label "Send to Kindle" (it says what the item does). No Amazon logos or artwork.
- **Not-affiliated line** in the manifest `description` and the README: "Unofficial: send ebooks to your Kindle by email or USB. Not created or endorsed by Amazon."
- **README.md** at the root, from the approved draft on branch `prototype/readme` (`docs/prototype/README.draft.md`): what sets it apart (keyboard Picker, email or USB per Book with EPUB conversion, Books held until the Kindle is plugged in, right-click entries), then Requires, Install, Configure, Use, Update, Remove (with the leftover cleanup commands) and Security.
- **LICENSE:** MIT, at the root.
- **preview.png** at the root: the Picker with demo Books plus a "Sent to Amazon…" notification, captured with demo data only, never real addresses.
- **Listing fields:** `author` sorydi3; category Productivity; tags `launcher`, `quickshell`, suggested extra tag `ebooks`.

### Fixes that ship with it

- `textFormat: Text.PlainText` on every `Text` in the Picker that lacks it (seven today), per Omarchy's plugin UI safety rule.
- `nautilus-python` optional in the extras script (Section 14).
- `PRODUCT.md` updated: published for Omarchy users; the name; the bar widget.

### Moving the author's install

From the old layout (copied plugin in `~/.local/share/kindle-send/omarchy-plugin`, symlinked as the plugin folder; `kindle-send` copied to `~/.local/share/kindle-send/bin` and linked from `~/.local/bin`):

1. Point `~/.config/omarchy/plugins/sorydi3.kindle-send` at the repo checkout's root (a symlink to the folder is allowed), and remove `~/.local/share/kindle-send/`.
2. Run the new extras script: it re-links `~/.local/bin/kindle-send` to the bundled program and replaces the old binding and menu blocks in place.
3. The first `kindle-send` run copies Settings from `shell.json` into `~/.config/kindle-send/settings.json`. The keyring password and the Send history (`~/.local/state/kindle-send/`) stay where they are.
4. Restart the shell, after checking nothing is waiting for the Kindle (Pending Sends live in memory).

### Going public (the author's manual checklist)

1. Make the GitHub repo public.
2. Check the root with `omarchy plugin validate .` and install it once from the public URL with `omarchy plugin add … --enable` on a clean user.
3. Submit the listing: open an issue on `omacom/omarchy-plugin-marketplace` with its form (repo URL, category, tags, the ownership statement). Expect the security scan to say "review-required" (the `sudo pacman -S calibre` hints); a maintainer accepts it.

