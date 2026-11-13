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
- [ ] The Omarchy menu has **Send to Kindle**, with **Send to Kindle** (opens the Picker) and **Setup** inside it. `omarchy menu summon kindle` opens the submenu.
- [ ] It prints `Enabled. Open the picker with: …`, and `omarchy plugin list` shows `sorydi3.kindle-send` as enabled.
- [ ] Nautilus windows close (`nautilus -q`). On the next start the extension is loaded.
- [ ] It asks `Run setup now …? [Y/n]`. Answer `n` for now. It prints `Run setup when ready: kindle-send setup`.
- [ ] `ls -l ~/.local/bin/kindle-send` is a link to `~/.local/share/kindle-send/bin/kindle-send`, and `~/.local/share/kindle-send/assets/test.epub` exists.
- [ ] Run the install again (and again with `--yes`). Neither file gains a second block: the script says `Already in …` for both.
- [ ] Run `./scripts/install.sh </dev/null` (no terminal). It skips both edits and says `Not added: no terminal to ask in …`.
- [ ] `SUPER + SHIFT + K` opens the Picker.
- [ ] Before setup, the Picker shows "Set up Send to Kindle".

## 2. Setup (§15.2)

Run from the menu: Send to Kindle → Setup. It should open a floating terminal.

- [ ] It asks, in order: Kindle address, Gmail address, app password (through `secret-tool store`), the Approved list step (waits for Enter), and Book folders (defaults filled in).
- [ ] The `sorydi3.kindle-send` entry in `~/.config/omarchy/shell.json` holds `kindleAddress`, `senderAddress`, `bookFolders`, `minEmailGapSeconds: 10` and `maxEmailsPerHour: 20`. The file mode is `600`, and the other plugins and keys are unchanged.
- [ ] `secret-tool lookup service kindle-send user <gmail>` prints a non-empty value. Don't paste it anywhere.
- [ ] `~/Books` exists.
- [ ] The test send runs, and "Kindle Send Test" appears on the Kindle within a few minutes. It was found through the installed link, so this also checks the test-EPUB path.
- [ ] Rerun setup and press Enter at every prompt. Every value is kept, the password included.
- [ ] The Picker no longer shows the setup line, without a shell restart.

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
- [ ] Clicking it opens setup in a floating terminal. Enter the right password there.

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
- [ ] **Notifications.** Progress replaces itself in one card (not a new card per stage). Normal summaries go after about 5 s. Critical ones stay. Clicking a setup-fixable failure opens setup.
- [ ] **Stage lines.** "Converting <Book>…" and "Copying to Kindle…" (with "i of n" for several Books) show during a USB Send.
- [ ] **Mixed Send held by the limit.** A Send that mixes USB Books and held emails ejects the Kindle as soon as its USB Books are copied, and posts its summary for them; the held emails are reported when they go.
- [ ] **Picker reload.** New settings from setup show the next time the Picker opens, without a shell restart.
- [ ] **QML loads in the live shell.** The Picker and the Service load without errors in `journalctl --user -u omarchy-shell` (or wherever the shell logs), since qmllint can't check injected members.

## 11. Settings in the Picker (§9)

- [ ] In the Book list the footer ends "Ctrl+,  Settings      Esc  Close" (or "Esc  Clear search" while searching).
- [ ] Type a comma in the Book list: it goes into the search. `Ctrl+,` opens Settings instead.
- [ ] Click the cog at the right end of the search line: Settings open.
- [ ] Settings show the Kindle address, the Gmail address and the Book folders as they are in `shell.json` (`~` kept), with the cursor in the Kindle address field. Typed text goes into the fields.
- [ ] `Tab` moves Kindle address → Gmail address → Book folders; `Shift+Tab` goes back. Focus never lands on the Book list behind.
- [ ] **Key isolation.** With Settings open, press `Enter`, `Space`, `Tab`, `Delete`, letters and arrows: no Book is sent, marked or switched, the search stays as it was, and no notification appears. Mouse clicks on the form don't mark Books either.
- [ ] Change a field: the footer says "Esc  Back (discard changes)". Press `Esc`: back in the Book list; reopen Settings and the old value is there.
- [ ] Clear the Gmail address and press `Enter` (from any field): "Needed before Books can be sent." replaces its help line in the accent color, focus jumps to it, the status line says "1 value needs fixing", and `shell.json` is unchanged. Type one letter: the problem goes and the help line is back.
- [ ] Save a Kindle address on `@kindle.cn` and a Book folder `~/Bokos`: saved (check `shell.json`), with the two warnings under their fields and "Saved. 2 values to check below.". `~/Bokos` isn't created. `shell.json` is still mode 600 and its other keys are untouched.
- [ ] Empty the Book folders field and save: it shows "~/Books, ~/Downloads" again.
- [ ] After a save, `Esc` returns to a Book list planned from the new folders.
