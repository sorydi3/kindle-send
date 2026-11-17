# Manual checks

The test suite runs everything against fakes: a temp HOME, a stub `omarchy`/`omarchy-shell`, a fake keyring, a fake SMTP server, fake `lsblk`/`udevadm`/`udisksctl`, and a fake `ebook-convert`. This list covers what only the real machine can show: the live shell, Gmail, Amazon, the Kindle, Nautilus and the notification server.

Work through it top to bottom on the target machine. Sections 1–9 follow spec §15 in order. Section 10 covers the rest of what was only faked. Tick each box as you go. Next to anything that fails, write what you saw.

Before you start:

- Have the Kindle (Paperwhite, USB id `1949:0324`) and its cable ready, unplugged.
- Put a small EPUB (a few hundred KB) in `~/Downloads`.
- Have a PDF over the Email limit (more than about 25 MB) and a `.cbz` file to hand.
- Have the Gmail app password ready, and check that the Gmail address is on Amazon's Approved Personal Document Email List.

## 1. Fresh install (§15.1)

Run `./scripts/install.sh` from the repo, in a terminal.

- [ ] The dependency check prints `python3, nautilus-python, secret-tool, udisksctl: found`. If Calibre is missing, it adds only the line `Optional: sudo pacman -S calibre to send EPUB over USB`. It never asks for a sudo password.
- [ ] It asks `Add SUPER + SHIFT + K (open the picker) to ~/.config/hypr/bindings.lua? [y/N]`. Answer `y`. `~/.config/hypr/bindings.lua.before-kindle-send` now exists, and the binding sits between `-- >>> kindle-send keybinding …` and `-- <<< kindle-send <<<` at the end of the file.
- [ ] It asks about the Omarchy menu. Answer `y`. `~/.config/omarchy/extensions/omarchy-menu.jsonc.before-kindle-send` now exists, and the three entries sit inside `// >>> kindle-send menu …` / `// <<< kindle-send <<<`, just before the final `}`.
- [ ] Your existing menu items (Snip …) still show in the Omarchy menu (`SUPER + SPACE`). If they vanished, the file no longer parses: report it.
- [ ] The Omarchy menu has **Send to Kindle**, with **Send to Kindle** (opens the Picker) and **Settings** (opens the Picker in Settings) inside it. `omarchy menu summon kindle` opens the submenu.
- [ ] It prints `Enabled. Open the picker with: …`, and `omarchy plugin list` shows `sorydi3.kindle-send` as enabled.
- [ ] Nautilus windows close (`nautilus -q`). On the next start the extension is loaded.
- [ ] It prints `Press SUPER + SHIFT + K to set up Send to Kindle in the Picker`, then asks `Set up in the terminal instead? [y/N]`. Answer `n`. It prints `Or set up in the terminal instead: kindle-send setup`.
- [ ] `ls -l ~/.local/bin/kindle-send` is a link to `~/.local/share/kindle-send/bin/kindle-send`, and `~/.local/share/kindle-send/assets/test.epub` exists.
- [ ] Run the install again (and again with `--yes`). Neither file gains a second block: the script says `Already in …` for both.
- [ ] Run `./scripts/install.sh </dev/null` (no terminal). It skips both edits and says `Not added: no terminal to ask in …`.
- [ ] `SUPER + SHIFT + K` opens the Picker.
- [ ] Before setup, the Picker shows "Set up Send to Kindle".

## 2. Setup (§15.2)

Run `kindle-send setup` in a terminal (the menu's Send to Kindle → Settings opens the Picker instead; see section 17).

- [ ] It asks, in order: Kindle address, Gmail address, app password (through `secret-tool store`), the Approved list step (waits for Enter), and Book folders (defaults filled in).
- [ ] The `sorydi3.kindle-send` entry in `~/.config/omarchy/shell.json` holds `kindleAddress`, `senderAddress`, `bookFolders`, `minEmailGapSeconds: 10` and `maxEmailsPerHour: 20`. The file mode is `600`, and the other plugins and keys are unchanged.
- [ ] `secret-tool lookup service kindle-send user <gmail>` prints a non-empty value. Don't paste it anywhere.
- [ ] `~/Books` exists.
- [ ] The test send runs, and "Kindle Send Test" appears on the Kindle within a few minutes. It was found through the installed link, so this also checks the test-EPUB path.
- [ ] Rerun setup and press Enter at every prompt. Every value is kept, the password included.
- [ ] The Picker now opens into the Book list, not Settings, without a shell restart.

## 3. Small EPUB by email (§15.3)

- [ ] The EPUB in `~/Downloads` shows Route **Email** in the Picker.
- [ ] Send it. One notification goes from "Sending…" to "Sent to Amazon. Should appear on your Kindle within a few minutes." It is normal urgency and disappears after about 5 s.
- [ ] It appears on the Kindle.
- [ ] Reopen the Picker. The Book is marked "sent just now".

## 4. Big PDF over USB, Pending Send (§15.4)

- [ ] The PDF over the Email limit shows Route **USB**, with "Too big for email (N MB)."
- [ ] With the Kindle unplugged, send it. A critical, lasting notification appears: "Waiting for Kindle: <Book>. Plug it in to send. Click to manage."
- [ ] Clicking the notification opens the Picker, with the line "1 Book waiting for Kindle" (or similar). `Delete` on that line cancels, and the notification changes to "Cancelled …".
- [ ] Send it again, still unplugged, then plug the Kindle in. Within a few seconds it goes "Copying to Kindle…", then "Copied to Kindle. Kindle ejected, safe to unplug".
- [ ] The file is in the Kindle's `documents/`, and the Kindle shows it in its library after unplugging.
- [ ] If the eject fails (for example, a file manager has the Kindle open), the summary says "Please eject the Kindle." and stays on screen.

## 5. EPUB over USB, Conversion (§15.5)

- [ ] With Calibre **not** installed: in the Picker, switch an EPUB to USB with `Tab` and send it. It fails with "Install calibre to send EPUB over USB (sudo pacman -S calibre)." in a critical notification.
- [ ] With Calibre installed (`sudo pacman -S calibre`, done by you): the same Send shows "Converting <Book>…", then "Copying to Kindle…". An `.azw3` lands in `documents/` and opens on the Kindle.

## 6. Nautilus (§15.6)

- [ ] Select a PDF and a CBZ in Nautilus and right-click. The menu shows "Send to Kindle".
- [ ] Choosing it opens the Picker with only the PDF listed and marked. A notification says "Left out 1 file(s)", naming the CBZ.
- [ ] Right-click a folder. There is no "Send to Kindle" item.

## 6b. Strata (if it's your file manager)

- [ ] Install printed `Added …/strata/actions/kindle-send/action.toml, turned off.` In Strata, Settings → Actions lists **Send to Kindle**, with nothing under Problems. Turn it on.
- [ ] Select one or more PDFs/EPUBs and right-click. **Send to Kindle** sits in the menu body (not under Actions).
- [ ] Choosing it opens the Picker with just those files, marked. Strata's Jobs panel shows the job as finished.
- [ ] A selection with a CBZ in it, or a folder, has no **Send to Kindle** item.
- [ ] A file named with spaces and accents (e.g. `Mon livre été.pdf`) opens in the Picker.
- [ ] Rerun install: the action stays turned on.

## 7. Send limit (§15.7)

Uses real email to your own Kindle, so 20 deliveries. If you'd rather not, lower `maxEmailsPerHour` to 3 in `shell.json` for the test, and put it back after.

- [ ] Mark 25 small Books and send them. Emails go out at least 10 s apart (check the times with `kindle-send history`).
- [ ] After the 20th (or the cap you set), the rest are held, with "Holding N Books to stay under Amazon's limit. Next in M min." The notice stays on screen (critical), its count drops as held Books go, and it ends as the summary of the held Books.
- [ ] While Books are held, send a Book by USB: it goes at once, its own notification shows progress, and the hold notice is left alone.
- [ ] Known limit: held Books are lost if the shell restarts. Not a failure.

## 8. Wrong app password (§15.8)

- [ ] Store a wrong password (`secret-tool store --label="kindle-send Gmail" service kindle-send user <gmail>`, type rubbish), then send a Book by email. A critical notification says "Gmail rejected the app password."
- [ ] Clicking it opens the Picker in Settings on the app password field, with "Gmail rejected the app password." under it (section 15). Paste the right password there and press Enter.

## 9. History and uninstall (§15.9)

- [ ] `kindle-send history` lists the Sends above, newest first, in local time, e.g. `Nov 4 23:17 · Dune.epub · Email · Sent to Amazon`, plus the USB lines and the `Failed: …` ones.
- [ ] Run `./scripts/uninstall.sh`. Afterwards:
  - [ ] `~/.config/omarchy/plugins/sorydi3.kindle-send`, `~/.local/bin/kindle-send`, `~/.local/share/kindle-send/` and `~/.local/share/nautilus-python/extensions/kindle-send.py` are gone.
  - [ ] The Picker is gone from the shell: `SUPER + SHIFT + K` does nothing, and `omarchy plugin list` doesn't show the plugin as loaded.
  - [ ] The binding block is gone from `bindings.lua`, and the rest of the file is as before (compare with `bindings.lua.before-kindle-send`).
  - [ ] The menu entries are gone, and your other menu items still show.
  - [ ] After Nautilus restarts, right-click has no "Send to Kindle".
  - [ ] `~/.config/strata/actions/kindle-send` is gone, and Strata's right-click has no "Send to Kindle".
  - [ ] Kept: the plugin's entry in `shell.json` (addresses, folders), the keyring password and `~/.local/state/kindle-send/history.jsonl`.
- [ ] Run `./scripts/install.sh` again. Your settings are still there (the Picker shows no setup line), and no block is added twice.
- [ ] (Optional) `./scripts/uninstall.sh --purge` also removes the `shell.json` entry, the keyring password and the history folder.

## 10. Things only faked in tests

These came up while building and aren't covered above.

- [ ] **Plugin unload without `omarchy plugin remove`.** Uninstall only removes the link and runs `omarchy-shell -q shell rescanPlugins`. It doesn't disable the plugin, because disabling deletes the plugin's `shell.json` entry and the settings with it. Check that the shell stops loading the plugin after the rescan, even though its entry stays in `plugins[]`. Check also that the shell logs nothing worse than a warning about it.
- [ ] **Enable keeps settings.** On a reinstall, `omarchy plugin enable` finds the existing entry and leaves its settings alone (§9 above covers it).
- [ ] **Rescan before enable.** On a fresh install, the plugin shows up in `omarchy plugin list` within about 2 s of the rescan. Otherwise install prints the warning `run: omarchy plugin enable sorydi3.kindle-send`.
- [ ] **Kindle detection on the real Paperwhite.** It is a whole-disk device with no partition table. `kindle-send kindle` prints `{"present": true, "mount": "/run/media/…", "free": N}` while plugged in and mounted by udiskie, and `{"present": false}` after unplugging.
- [ ] **Eject.** `kindle-send eject` unmounts and powers off the Kindle (`{"ejected": true}`). The Kindle leaves USB mode.
- [ ] **Real SMTP.** Gmail's advertised `SIZE` is cached in `~/.local/state/kindle-send/email-limit.json` after the first send, and `kindle-send plan` estimates the Email limit from it.
- [ ] **Notifications.** Progress replaces itself in one card (not a new card per stage). Normal summaries go after about 5 s. Critical ones stay. Clicking a failure a Setting fixes opens Settings in the Picker on that field (section 15).
- [ ] **Stage lines.** "Converting <Book>…" and "Copying to Kindle…" (with "i of n" for several Books) show during a USB Send.
- [ ] **Mixed Send held by the limit.** A Send that mixes USB Books and held emails ejects the Kindle as soon as its USB Books are copied, and posts its summary for them; the held emails are reported when they go.
- [ ] **Picker reload.** New settings from setup show the next time the Picker opens, without a shell restart.
- [ ] **QML loads in the live shell.** The Picker and the Service load without errors in `journalctl --user -u omarchy-shell` (or wherever the shell logs), since qmllint can't check injected members.

## 11. Settings in the Picker (§9)

- [ ] In the Book list the footer ends "Ctrl+,  Settings      Esc  Close" (or "Esc  Clear search" while searching).
- [ ] Type a comma in the Book list: it goes into the search. `Ctrl+,` opens Settings instead.
- [ ] Click the cog at the right end of the search line: Settings open.
- [ ] Settings show the Kindle address, the Gmail address and the Book folders as they are in `shell.json` (`~` kept), with the cursor in the Kindle address field. Typed text goes into the fields.
- [ ] `Tab` moves Kindle address → Gmail address → app password → Book folders; `Shift+Tab` goes back. Focus never lands on the Book list behind.
- [ ] **Key isolation.** With Settings open, press `Enter`, `Space`, `Tab`, `Delete`, letters and arrows: no Book is sent, marked or switched, the search stays as it was, and no notification appears. Mouse clicks on the form don't mark Books either.
- [ ] Change a field: the footer says "Esc  Back (discard changes)". Press `Esc`: back in the Book list; reopen Settings and the old value is there.
- [ ] Clear the Gmail address and press `Enter` (from any field): "Needed before Books can be sent." replaces its help line in the accent color, focus jumps to it, the status line says "1 value needs fixing.", and `shell.json` is unchanged. Type one letter: the problem goes and the help line is back.
- [ ] Save a Kindle address on `@kindle.cn` and a Book folder `~/Bokos`: saved (check `shell.json`), with the two warnings under their fields and "Saved. 2 values to check below.". `~/Bokos` isn't created. `shell.json` is still mode 600 and its other keys are untouched.
- [ ] Empty the Book folders field and save: it shows "~/Books, ~/Downloads" again.
- [ ] After a save, `Esc` returns to a Book list planned from the new folders.

## 12. Help links in Settings (§9, Links)

- [ ] In Settings, the footer shows "Ctrl+O  Open link" on the Kindle address and the Gmail address (and the app password, once that field exists), and not on Book folders.
- [ ] On the Kindle address, press `Ctrl+O`: the Picker closes and the browser shows Amazon's Manage Your Content and Devices.
- [ ] On the Gmail address, press `Ctrl+O`: the browser shows Amazon's Personal Document Settings, where the approved list is. No "done?" question follows.
- [ ] On the app password (once it exists), `Ctrl+O` opens myaccount.google.com/apppasswords.
- [ ] Click the underlined help line under the Kindle address: same as `Ctrl+O`. Book folders' help line isn't underlined and does nothing on click. A problem shown in place of a help line isn't a link.
- [ ] **Round trip.** Change the Kindle address without saving, move to the Gmail address and press `Ctrl+O`. After the browser shows, press `SUPER + SHIFT + K`: the Picker opens in Settings, the changed Kindle address is still there, the cursor is in the Gmail address, and the footer says "Esc  Back (discard changes)". `shell.json` is unchanged.
- [ ] After that round trip, `Esc` goes back to the Book list; closing and reopening the Picker now opens the Book list, not Settings.
- [ ] Save with a warning, then follow a link and come back: the warning and the status line are still shown.

## 13. App password in Settings (§9, ADR 0001)

- [ ] Settings show "Gmail app password" between the Gmail address and the Book folders (so `Tab` now goes Kindle address → Gmail address → app password → Book folders). Its help line reads "Create one at myaccount.google.com/apppasswords. It needs 2-Step Verification."
- [ ] With a password stored, the field is empty with "Stored. Type to replace it." in grey; without one, "xxxx xxxx xxxx xxxx". Typed characters show as dots.
- [ ] Type a wrong app password and press `Enter`: the status line says "Checking the app password with Gmail…", then "Gmail rejected this app password." replaces the help line, focus jumps to the field, and `shell.json` and the keyring (`secret-tool lookup service kindle-send user <Gmail>`) are unchanged.
- [ ] Type the real app password and save: "Saved.", the field empties and shows "Stored. Type to replace it.", and `secret-tool lookup service kindle-send user <Gmail>` prints it.
- [ ] While that save runs, `ps -eo args | grep kindle-send` and `ps -eo args | grep secret-tool` never show the password, and it isn't in `shell.json` or the journal (`journalctl --user -b | grep -F '<first 4 characters>'`).
- [ ] Turn Wi-Fi off, type the password and save: saved anyway, with "Couldn't reach Gmail to check the password. Saved anyway." under the field.
- [ ] Change only the Kindle address and save: the status line goes straight to "Saved." with no "Checking…".
- [ ] Type a password, then press `Esc`: back in the Book list; reopen Settings and the field is empty again.

## 14. Browse for a Book folder (§9, Book folders)

- [ ] In Settings, the footer shows "Ctrl+B  Browse" on Book folders only, and a "Browse…" button sits beside the Book folders field. `Tab` skips the button (Kindle address → Gmail address → app password → Book folders).
- [ ] On Book folders, press `Ctrl+B`: the Picker closes and the GTK folder chooser opens, titled "Add a Book folder", in the home folder. `Ctrl+B` on any other field does nothing.
- [ ] **Round trip.** Change the Kindle address without saving, click "Browse…", pick a folder inside home (e.g. `~/Documents`) with the mouse and confirm: the Picker reopens in Settings by itself, with the changed Kindle address still there, `~/Documents` appended to Book folders (written with `~`), the cursor in Book folders, and the footer saying "Esc  Back (discard changes)". `shell.json` is unchanged until `Enter`.
- [ ] Pick a folder outside home (e.g. `/tmp`): it's appended as its full path. Pick a folder already in the field: nothing is added twice. Pick a folder with a space or an accent in its name: it shows as typed, not `%20`.
- [ ] Open the chooser and cancel it (Cancel, or `Esc`): the Picker reopens in Settings with the field and any unsaved values as they were.
- [ ] Inside the chooser, `Ctrl+L` does nothing (known, spec §16); picking takes the mouse.
- [ ] After a Browse, press `Enter`: the folder is saved and the Book list (after `Esc`) lists Books from it.

## 15. Failure notifications open Settings (§10, §13)

Back up `~/.config/omarchy/shell.json` first and put it back afterwards.

- [ ] Remove `kindleAddress` from the plugin's entry in `shell.json` (keep the app password stored) and send a Book by email. The critical notification says "Not set up: kindleAddress missing." Clicking it opens the Picker in Settings, the cursor in the Kindle address, "Needed before Books can be sent." in place of its help line. No terminal opens.
- [ ] Same with `senderAddress` removed: the click lands on the Gmail address, flagged the same way.
- [ ] Clear the stored password (`secret-tool clear service kindle-send user <Gmail>`) and send by email: "No app password stored." Clicking it opens Settings on the app password field with "No app password stored." under it.
- [ ] Section 8's wrong password: the click lands on the app password field with "Gmail rejected the app password." under it. Type the right one: the problem clears as you type; `Enter` saves it.
- [ ] From the wrong-password case, `Esc` goes back to the Book list (not the terminal). From the missing-value cases setup is needed, so the form is titled "Set up Send to Kindle" and `Esc` closes the Picker (section 16). A failure no Setting fixes (e.g. "Too big for email") does nothing on click.

## 16. First run opens straight into Settings (§4 Setup needed, §9)

Start from no setup: move the `sorydi3.kindle-send` keys out of `shell.json` (keep a copy) and `secret-tool clear service kindle-send user <Gmail>`, and move `~/Books` aside if it's empty.

- [ ] `SUPER + SHIFT + K` opens straight into the form titled "Set up Send to Kindle". No Book list, no "Start setup" screen, and no terminal opens.
- [ ] Kindle address, Gmail address and Gmail app password each show "· needed" beside their label in the accent color; Book folders doesn't. The footer ends "Esc  Close".
- [ ] Press `Esc`: the Picker closes. Open it again: back in "Set up Send to Kindle".
- [ ] Type a Kindle address: its "· needed" goes at once. Press `Enter` with the others still empty: the status line says "2 still needed before Books can be sent.", "Needed before Books can be sent." replaces both help lines, focus jumps to the Gmail address, and `shell.json` is unchanged.
- [ ] Fill in the Gmail address and the real app password and press `Enter`: saved. The title changes to "Settings", no field is flagged, `~/Books` now exists, and the footer ends "Esc  Back to Books". `Esc` shows the Book list.
- [ ] Delete `~/Books` (if empty), change only the Kindle address in Settings and save: `~/Books` is not created again.
- [ ] With Book folders pointing at empty folders, the Picker says "No Books found in …" with "Enter  Change Book folders". `Enter` (or a click on the message) opens Settings with the cursor in Book folders.
- [ ] `kindle-send setup` in a terminal still runs the wizard.
- [ ] Put back your own `shell.json` keys and app password.

## 17. Omarchy menu opens Settings (§14)

Back up `~/.config/omarchy/extensions/omarchy-menu.jsonc` first.

- [ ] Over an install from before Settings moved into the Picker (the menu shows Send to Kindle → Setup), run `./scripts/install.sh` in a terminal. It asks `Replace the older Send to Kindle entries in …? [y/N]`. Answer `y`: it says `Updated in …`, and the block sits where it was, with **Settings** in place of **Setup**.
- [ ] Once set up, Omarchy menu → Send to Kindle → Settings opens the Picker in Settings, no field flagged, no terminal. `Esc` goes back to the Book list.
- [ ] Run the install again: `Already in …` for the menu.
- [ ] `./scripts/uninstall.sh` removes the block; the rest of the menu still shows.

## 18. Test send from Settings (§9 Test send, §10)

Sends one real email to your own Kindle. Start from section 16's state just before the first save.

- [ ] Save the form for the first time: the status line says "Saved. Ctrl+T sends a test Book to check it all works."
- [ ] Type in any field without saving and press `Ctrl+T`: nothing is sent; the status line says "Save first, then Ctrl+T sends a test Book." `Esc`, reopen Settings with `Ctrl+,`.
- [ ] With everything saved, press `Ctrl+T`: the Picker stays in Settings, the status line says "Sending a test Book…", then "Gmail accepted the test Book at <time>. Check your Kindle in a few minutes." A second `Ctrl+T` while it is sending sends nothing more.
- [ ] The notification is headed "Kindle Send Test" and reads "Sent to Amazon. Not on your Kindle in a few minutes? Check that <Gmail> is on Amazon's approved list and the Kindle address is right." Clicking it (before it goes) opens the Picker in Settings.
- [ ] "Kindle Send Test" arrives on the Kindle. `kindle-send history` lists "Kindle Send Test.epub" by Email, sent.
- [ ] With section 8's wrong app password stored, `Ctrl+T`: the status line says "Couldn't send the test Book.", "Gmail rejected the app password." replaces the app password's help line and the cursor is there. The critical notification's click opens Settings on that field.
- [ ] With the network off, `Ctrl+T`: the status line says "Couldn't send the test Book." followed by the reason. Clicking its critical notification does nothing: no Setting fixes it.

## 19. Settings in a light and a dark theme (PRODUCT.md look)

Settings draw with the Omarchy theme's tokens only, so they follow the theme. Switch themes from the Omarchy menu (Style → Theme); no restart is needed.

- [ ] With a dark theme (e.g. Tokyo Night), open Settings with `Ctrl+,`: the title, labels, field text, placeholders, help lines, the status line and the footer are all readable on the card; the focused field and the "· needed" flag stand out in the theme's accent color.
- [ ] Type a wrong value and save, so a problem replaces a help line: it reads in the accent color, clearly apart from the help lines.
- [ ] Switch to a light theme (e.g. Catppuccin Latte) and repeat: nothing keeps a dark-theme color (no dark text boxes, no white-on-white text), and the same text is readable.

## 20. The repo root is the plugin (#59)

The plugin's `manifest.json`, QML and JS now sit at the repo root; nothing else changed.

- [ ] `omarchy plugin validate .` at the repo root prints no error.
- [ ] Run `./scripts/install.sh` in a temp `HOME` (not your own). `~/.local/share/kindle-send/omarchy-plugin` holds only `manifest.json`, the `*.qml` and the `*.js`, and the plugin link points at it.
- [ ] After installing for real, `SUPER + SHIFT + K` opens the Picker and a Send works as before.

## 21. The Picker and Service run the bundled kindle-send (#60)

They run `bin/kindle-send` from the plugin folder, never a `kindle-send` on PATH.

- [ ] With `~/.local/bin/kindle-send` moved aside (so none is on PATH), restart the shell and press `SUPER + SHIFT + K`: the Picker lists Books, `Ctrl+,` shows Settings, and a Send by email and by USB both go through. Put it back afterwards.
- [ ] With the plugin folder a symlink to the repo checkout, `Ctrl+T` in Settings sends "Kindle Send Test" (the test EPUB is found beside the bundled program).
- [ ] After `./scripts/install.sh` in a temp `HOME`, the copied plugin also holds `bin/kindle-send` (executable) and `assets/test.epub` besides the files section 20 lists.
