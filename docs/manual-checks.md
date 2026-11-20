# Manual checks

The test suite runs everything against fakes: a temp HOME, a stub `omarchy`/`omarchy-shell`, a fake keyring, a fake SMTP server, fake `lsblk`/`udevadm`/`udisksctl`, and a fake `ebook-convert`. This list covers what only the real machine can show: the live shell, Gmail, Amazon, the Kindle, Nautilus and the notification server.

Work through it top to bottom on the target machine. Sections 1–9 follow spec §15 in order. Section 10 covers the rest of what was only faked. Tick each box as you go. Next to anything that fails, write what you saw.

Before you start:

- Have the Kindle (Paperwhite, USB id `1949:0324`) and its cable ready, unplugged.
- Put a small EPUB (a few hundred KB) in `~/Downloads`.
- Have a PDF over the Email limit (more than about 25 MB) and a `.cbz` file to hand.
- Have the Gmail app password ready, and check that the Gmail address is on Amazon's Approved Personal Document Email List.

## 1. Fresh install (§15.1)

Install the plugin (`omarchy plugin add … --enable`, or the plugin folder linked to the checkout), then run the extras script `~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh` in a terminal (section 26 has the details).

- [ ] The dependency check prints `python3, secret-tool: found`. If Calibre is missing, it adds only the line `Optional: sudo pacman -S calibre to send EPUB over USB`. It never asks for a sudo password.
- [ ] It asks to link `~/.local/bin/kindle-send`, then about the Nautilus item (and the Strata action, with Strata). Answer `y` to each.
- [ ] It asks `Add SUPER + SHIFT + K (open the Picker) to ~/.config/hypr/bindings.lua? [y/N]`. Answer `y`. `~/.config/hypr/bindings.lua.before-kindle-send` now exists, and the binding sits between `-- >>> kindle-send keybinding …` and `-- <<< kindle-send <<<` at the end of the file.
- [ ] It asks about the Omarchy menu. Answer `y`. `~/.config/omarchy/extensions/omarchy-menu.jsonc.before-kindle-send` now exists, and the three entries sit inside `// >>> kindle-send menu …` / `// <<< kindle-send <<<`, just before the final `}`.
- [ ] Your existing menu items (Snip …) still show in the Omarchy menu (`SUPER + SPACE`). If they vanished, the file no longer parses: report it.
- [ ] The Omarchy menu has **Books to Kindle**, with **Books to Kindle** (opens the Picker) and **Settings** (opens the Picker in Settings) inside it. `omarchy menu summon kindle` opens the submenu.
- [ ] Nautilus windows close (`nautilus -q`). On the next start the extension is loaded.
- [ ] It prints `Open the Picker from the Books to Kindle bar widget (or press SUPER + SHIFT + K) to set it up in Settings.`, then asks `Set up in the terminal instead? [y/N]`. Answer `n`. It prints `Or set up in the terminal instead: kindle-send setup`.
- [ ] `ls -l ~/.local/bin/kindle-send` is a link to the plugin folder's `bin/kindle-send`.
- [ ] Run the script again (and again with `--yes`). Nothing changes: it says `Already …` for each extra and asks only about terminal setup.
- [ ] Run it with `</dev/null` (no terminal). It changes nothing and says `No terminal to ask in, so nothing is changed …`.
- [ ] `SUPER + SHIFT + K` opens the Picker.
- [ ] Before setup, the Picker opens straight into Settings, titled "Set up Books to Kindle" (section 16).

## 2. Setup (§15.2)

Run `kindle-send setup` in a terminal (the menu's Books to Kindle → Settings opens the Picker instead; see section 17).

- [ ] It asks, in order: Kindle address, Gmail address, app password (through `secret-tool store`), the Approved list step (waits for Enter), and Book folders (defaults filled in).
- [ ] `~/.config/kindle-send/settings.json` holds `kindleAddress`, `senderAddress`, `bookFolders`, `minEmailGapSeconds: 10` and `maxEmailsPerHour: 20`. The file mode is `600`, and `~/.config/omarchy/shell.json` is unchanged.
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

Uses real email to your own Kindle, so 20 deliveries. If you'd rather not, lower `maxEmailsPerHour` to 3 in `settings.json` for the test, and put it back after.

- [ ] Mark 25 small Books and send them. Emails go out at least 10 s apart (check the times with `kindle-send history`).
- [ ] After the 20th (or the cap you set), the rest are held, with "Holding N Books to stay under Amazon's limit. Next in M min." The notice stays on screen (critical), its count drops as held Books go, and it ends as the summary of the held Books.
- [ ] While Books are held, send a Book by USB: it goes at once, its own notification shows progress, and the hold notice is left alone.
- [ ] Known limit: held Books are lost if the shell restarts. Not a failure.

## 8. Wrong app password (§15.8)

- [ ] Store a wrong password (`secret-tool store --label="kindle-send Gmail" service kindle-send user <gmail>`, type rubbish), then send a Book by email. A critical notification says "Gmail rejected the app password."
- [ ] Clicking it opens the Picker in Settings on the app password field, with "Gmail rejected the app password." under it (section 15). Paste the right password there and press Enter.

## 9. History and uninstall (§15.9)

- [ ] `kindle-send history` lists the Sends above, newest first, in local time, e.g. `Nov 4 23:17 · Dune.epub · Email · Sent to Amazon`, plus the USB lines and the `Failed: …` ones.
- [ ] Run `scripts/install.sh --remove` from the plugin folder. Afterwards:
  - [ ] `~/.local/bin/kindle-send` and `~/.local/share/nautilus-python/extensions/kindle-send.py` are gone.
  - [ ] The binding block is gone from `bindings.lua`, and the rest of the file is as before (compare with `bindings.lua.before-kindle-send`).
  - [ ] The menu entries are gone, and your other menu items still show.
  - [ ] After Nautilus restarts, right-click has no "Send to Kindle".
  - [ ] `~/.config/strata/actions/kindle-send` is gone, and Strata's right-click has no "Send to Kindle".
  - [ ] Kept: `~/.config/kindle-send/settings.json`, the keyring password and `~/.local/state/kindle-send/history.jsonl`. The script ends by pointing to `omarchy plugin remove sorydi3.kindle-send`.
- [ ] Run `scripts/install.sh` again. Your settings are still there (the Picker shows no setup line), and no block is added twice.
- [ ] (Optional) `scripts/install.sh --purge` also removes `~/.config/kindle-send/`, the keyring password and the history folder; `shell.json` is unchanged.

## 10. Things only faked in tests

These came up while building and aren't covered above.

- [ ] **Plugin removal.** After `scripts/install.sh --remove`, `omarchy plugin remove sorydi3.kindle-send` stops the shell loading the plugin (the bar icon goes, `SUPER + SHIFT + K` does nothing), and the shell logs nothing worse than a warning about it.
- [ ] **Settings survive a reinstall.** Then `omarchy plugin add https://github.com/sorydi3/kindle-send --enable` again: the Picker opens into the Book list with the old Settings, since they live in `~/.config/kindle-send/settings.json`, not in the plugin's `shell.json` entry (ADR 0002).
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
- [ ] Settings show the Kindle address, the Gmail address and the Book folders as they are in `settings.json` (`~` kept), with the cursor in the Kindle address field. Typed text goes into the fields.
- [ ] `Tab` moves Kindle address → Gmail address → app password → Book folders; `Shift+Tab` goes back. Focus never lands on the Book list behind.
- [ ] **Key isolation.** With Settings open, press `Enter`, `Space`, `Tab`, `Delete`, letters and arrows: no Book is sent, marked or switched, the search stays as it was, and no notification appears. Mouse clicks on the form don't mark Books either.
- [ ] Change a field: the footer says "Esc  Back (discard changes)". Press `Esc`: back in the Book list; reopen Settings and the old value is there.
- [ ] Clear the Gmail address and press `Enter` (from any field): "Needed before Books can be sent." replaces its help line in the accent color, focus jumps to it, the status line says "1 value needs fixing.", and `settings.json` is unchanged. Type one letter: the problem goes and the help line is back.
- [ ] Save a Kindle address on `@kindle.cn` and a Book folder `~/Bokos`: saved (check `settings.json`), with the two warnings under their fields and "Saved. 2 values to check below.". `~/Bokos` isn't created. `settings.json` is still mode 600 and its other keys (the Send limit numbers) are untouched.
- [ ] Empty the Book folders field and save: it shows "~/Books, ~/Downloads" again.
- [ ] After a save, `Esc` returns to a Book list planned from the new folders.

## 12. Help links in Settings (§9, Links)

- [ ] In Settings, the footer shows "Ctrl+O  Open link" on the Kindle address and the Gmail address (and the app password, once that field exists), and not on Book folders.
- [ ] On the Kindle address, press `Ctrl+O`: the Picker closes and the browser shows Amazon's Manage Your Content and Devices.
- [ ] On the Gmail address, press `Ctrl+O`: the browser shows Amazon's Personal Document Settings, where the approved list is. No "done?" question follows.
- [ ] On the app password (once it exists), `Ctrl+O` opens myaccount.google.com/apppasswords.
- [ ] Click the underlined help line under the Kindle address: same as `Ctrl+O`. Book folders' help line isn't underlined and does nothing on click. A problem shown in place of a help line isn't a link.
- [ ] **Round trip.** Change the Kindle address without saving, move to the Gmail address and press `Ctrl+O`. After the browser shows, press `SUPER + SHIFT + K`: the Picker opens in Settings, the changed Kindle address is still there, the cursor is in the Gmail address, and the footer says "Esc  Back (discard changes)". `settings.json` is unchanged.
- [ ] After that round trip, `Esc` goes back to the Book list; closing and reopening the Picker now opens the Book list, not Settings.
- [ ] Save with a warning, then follow a link and come back: the warning and the status line are still shown.

## 13. App password in Settings (§9, ADR 0001)

- [ ] Settings show "Gmail app password" between the Gmail address and the Book folders (so `Tab` now goes Kindle address → Gmail address → app password → Book folders). Its help line reads "Create one at myaccount.google.com/apppasswords. It needs 2-Step Verification."
- [ ] With a password stored, the field is empty with "Stored. Type to replace it." in grey; without one, "xxxx xxxx xxxx xxxx". Typed characters show as dots.
- [ ] Type a wrong app password and press `Enter`: the status line says "Checking the app password with Gmail…", then "Gmail rejected this app password." replaces the help line, focus jumps to the field, and `settings.json` and the keyring (`secret-tool lookup service kindle-send user <Gmail>`) are unchanged.
- [ ] Type the real app password and save: "Saved.", the field empties and shows "Stored. Type to replace it.", and `secret-tool lookup service kindle-send user <Gmail>` prints it.
- [ ] While that save runs, `ps -eo args | grep kindle-send` and `ps -eo args | grep secret-tool` never show the password, and it isn't in `settings.json` or the journal (`journalctl --user -b | grep -F '<first 4 characters>'`).
- [ ] Turn Wi-Fi off, type the password and save: saved anyway, with "Couldn't reach Gmail to check the password. Saved anyway." under the field.
- [ ] Change only the Kindle address and save: the status line goes straight to "Saved." with no "Checking…".
- [ ] Type a password, then press `Esc`: back in the Book list; reopen Settings and the field is empty again.

## 14. Browse for a Book folder (§9, Book folders)

- [ ] In Settings, the footer shows "Ctrl+B  Browse" on Book folders only, and a "Browse…" button sits beside the Book folders field. `Tab` skips the button (Kindle address → Gmail address → app password → Book folders).
- [ ] On Book folders, press `Ctrl+B`: the Picker closes and the GTK folder chooser opens, titled "Add a Book folder", in the home folder. `Ctrl+B` on any other field does nothing.
- [ ] **Round trip.** Change the Kindle address without saving, click "Browse…", pick a folder inside home (e.g. `~/Documents`) with the mouse and confirm: the Picker reopens in Settings by itself, with the changed Kindle address still there, `~/Documents` appended to Book folders (written with `~`), the cursor in Book folders, and the footer saying "Esc  Back (discard changes)". `settings.json` is unchanged until `Enter`.
- [ ] Pick a folder outside home (e.g. `/tmp`): it's appended as its full path. Pick a folder already in the field: nothing is added twice. Pick a folder with a space or an accent in its name: it shows as typed, not `%20`.
- [ ] Open the chooser and cancel it (Cancel, or `Esc`): the Picker reopens in Settings with the field and any unsaved values as they were.
- [ ] Inside the chooser, `Ctrl+L` does nothing (known, spec §16); picking takes the mouse.
- [ ] After a Browse, press `Enter`: the folder is saved and the Book list (after `Esc`) lists Books from it.

## 15. Failure notifications open Settings (§10, §13)

Back up `~/.config/kindle-send/settings.json` first and put it back afterwards.

- [ ] Remove `kindleAddress` from `settings.json` (keep the app password stored) and send a Book by email. The critical notification says "Not set up: kindleAddress missing." Clicking it opens the Picker in Settings, the cursor in the Kindle address, "Needed before Books can be sent." in place of its help line. No terminal opens.
- [ ] Same with `senderAddress` removed: the click lands on the Gmail address, flagged the same way.
- [ ] Clear the stored password (`secret-tool clear service kindle-send user <Gmail>`) and send by email: "No app password stored." Clicking it opens Settings on the app password field with "No app password stored." under it.
- [ ] Section 8's wrong password: the click lands on the app password field with "Gmail rejected the app password." under it. Type the right one: the problem clears as you type; `Enter` saves it.
- [ ] From the wrong-password case, `Esc` goes back to the Book list (not the terminal). From the missing-value cases setup is needed, so the form is titled "Set up Books to Kindle" and `Esc` closes the Picker (section 16). A failure no Setting fixes (e.g. "Too big for email") does nothing on click.

## 16. First run opens straight into Settings (§4 Setup needed, §9)

Start from no setup: move `~/.config/kindle-send/settings.json` aside (keep it) and `secret-tool clear service kindle-send user <Gmail>`, and move `~/Books` aside if it's empty.

- [ ] `SUPER + SHIFT + K` opens straight into the form titled "Set up Books to Kindle". No Book list, no "Start setup" screen, and no terminal opens.
- [ ] Kindle address, Gmail address and Gmail app password each show "· needed" beside their label in the accent color; Book folders doesn't. The footer ends "Esc  Close".
- [ ] Press `Esc`: the Picker closes. Open it again: back in "Set up Books to Kindle".
- [ ] Type a Kindle address: its "· needed" goes at once. Press `Enter` with the others still empty: the status line says "2 still needed before Books can be sent.", "Needed before Books can be sent." replaces both help lines, focus jumps to the Gmail address, and no `settings.json` is written.
- [ ] Fill in the Gmail address and the real app password and press `Enter`: saved. The title changes to "Settings", no field is flagged, `~/Books` now exists, and the footer ends "Esc  Back to Books". `Esc` shows the Book list.
- [ ] Delete `~/Books` (if empty), change only the Kindle address in Settings and save: `~/Books` is not created again.
- [ ] With Book folders pointing at empty folders, the Picker says "No Books found in …" with "Enter  Change Book folders". `Enter` (or a click on the message) opens Settings with the cursor in Book folders.
- [ ] `kindle-send setup` in a terminal still runs the wizard.
- [ ] Put back your own `settings.json` and app password.

## 17. Omarchy menu opens Settings (§14)

Back up `~/.config/omarchy/extensions/omarchy-menu.jsonc` first.

- [ ] Over an install from before Settings moved into the Picker (the menu shows Send to Kindle → Setup), run `./scripts/install.sh` in a terminal. It asks `Replace the older Send to Kindle entries in …? [y/N]`. Answer `y`: it says `Updated in …`, and the block sits where it was, with **Settings** in place of **Setup**.
- [ ] Once set up, Omarchy menu → Books to Kindle → Settings opens the Picker in Settings, no field flagged, no terminal. `Esc` goes back to the Book list.
- [ ] Run the install again: `Already in …` for the menu.
- [ ] `scripts/install.sh --remove` removes the block; the rest of the menu still shows.

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
- [ ] (Retired by #66: the extras script no longer copies the plugin; `omarchy plugin add` installs it.)
- [ ] After installing for real, `SUPER + SHIFT + K` opens the Picker and a Send works as before.

## 21. Bar widget (#62, spec §17)

Add the widget to a test bar layout yourself (the Omarchy bar settings), not with `omarchy bar put`. Start with nothing waiting.

- [ ] A book icon shows, with no number beside it. Hover: the tooltip reads "Books to Kindle" and, below, "Nothing waiting".
- [ ] Left-click opens the Picker; left-click again closes it. Middle-click and right-click do nothing.
- [ ] With the Kindle unplugged, send two Books by USB: "2" shows beside the icon, and the tooltip says "2 waiting for Kindle". Plug the Kindle in: while the Send runs the icon takes the bar's active colour and the tooltip says "Sending…"; afterwards the number goes and the colour is back to normal.
- [ ] With emails held by the Send limit (section 7), the number counts them too and the tooltip adds "N held by the Send limit" (joined with " · " to anything else).
- [ ] With a dark theme (e.g. Tokyo Night) the icon, the number and the tooltip are readable on the bar, and the active colour stands out. Switch to a light theme (e.g. Catppuccin Latte): the same, with nothing keeping a dark-theme colour.

## 22. The name is Books to Kindle (#63)

The plugin shows itself as "Books to Kindle"; only the right-click action keeps the label "Send to Kindle".

- [ ] `omarchy plugin validate .` passes; `manifest.json` has name "Books to Kindle", version 1.0.0, author sorydi3, license MIT and the "Unofficial: … Not created or endorsed by Amazon." description.
- [ ] While setup is needed, the Picker opens into Settings titled "Set up Books to Kindle". The Book list's search line reads "Books to Kindle…" while empty.
- [ ] A Send's notification shows the app name "Books to Kindle".
- [ ] Run the extras script in a temp `HOME` with an Omarchy menu file holding a "Send to Kindle" block: it offers to replace it, and afterwards the menu shows "Books to Kindle" with "Books to Kindle" and "Settings" inside.
- [ ] The Nautilus and Strata right-click items still read "Send to Kindle".

## 23. Settings live in their own file (#61, ADR 0002)

Back up `~/.config/omarchy/shell.json` and `~/.config/kindle-send/` first, and put them back afterwards.

- [ ] **The one-time copy.** Move `~/.config/kindle-send/settings.json` aside and put `kindleAddress`, `senderAddress` and `bookFolders` in the plugin's old `sorydi3.kindle-send` entry in `shell.json`. Open the Picker: Settings show those values, and `~/.config/kindle-send/settings.json` now holds them, mode `600`. `shell.json` is byte for byte what it was (`cmp` against the backup).
- [ ] Change the Kindle address in the old `shell.json` entry and reopen Settings: they still show the copied one. `shell.json` is never read again.
- [ ] Save Settings from the Picker and run `kindle-send setup` once: `shell.json` is still unchanged, and `settings.json` keeps `minEmailGapSeconds` and `maxEmailsPerHour`.
- [ ] **Disable and enable.** Disable the plugin in omarchy and enable it again: Settings are all still there, and saving them doesn't enable a disabled plugin.

## 24. The Picker and Service run the bundled kindle-send (#60)

They run `bin/kindle-send` from the plugin folder, never a `kindle-send` on PATH.

- [ ] With `~/.local/bin/kindle-send` moved aside (so none is on PATH), restart the shell and press `SUPER + SHIFT + K`: the Picker lists Books, `Ctrl+,` shows Settings, and a Send by email and by USB both go through. Put it back afterwards.
- [ ] With the plugin folder a symlink to the repo checkout, `Ctrl+T` in Settings sends "Kindle Send Test" (the test EPUB is found beside the bundled program).
- [ ] (Retired by #66: the extras script no longer copies the plugin; the link in `~/.local/bin` points at the bundled `bin/kindle-send`, section 26.)

## 25. Message codes and Route ids (#64)

The Picker still shows the English text; only where Route labels come from changed.

- [ ] The Picker shows "Email" and "USB" on each row, in the footer ("USB can't take 1") and in the details ("switched to USB") as before.
- [ ] `kindle-send plan --folders` prints no `routeLabels`; each Book has `routeReasonCode` and `routeReasonValues`.
- [ ] `kindle-send history` and `kindle-send setup` read exactly as before (English, no codes).

## 26. Extras script, --remove and --purge (#66, spec §14)

Run it from the plugin folder (`~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh`). Try it first in a temp `HOME` (`HOME=$(mktemp -d) XDG_CONFIG_HOME= XDG_STATE_HOME= XDG_DATA_HOME= …`) before your own; back up `~/.config/hypr/bindings.lua` and `~/.config/omarchy/extensions/omarchy-menu.jsonc` first.

- [ ] It never copies the plugin, never runs `omarchy plugin enable`, and `~/.local/share/kindle-send/` is not created.
- [ ] In a terminal it asks before each extra, in order: the `~/.local/bin/kindle-send` link, the Nautilus item, the Strata action (only with Strata), the binding, the menu entries. Answer `n` to the link: it skips Nautilus and Strata without asking ("need the kindle-send link").
- [ ] With `nautilus-python` uninstalled (or `KINDLE_SEND_NAUTILUS_PYTHON=/nonexistent`), it says `nautilus-python is not installed; skipped …` and adds the rest.
- [ ] Over the old layout (link to `~/.local/share/kindle-send/bin/kindle-send`, a "Send to Kindle" binding block), it offers `Replace the older …` for the link and the binding; afterwards the link points at the plugin folder's `bin/kindle-send` and the binding block, in the same place, says "Books to Kindle".
- [ ] A second run with `--yes` changes nothing and Nautilus isn't restarted.
- [ ] `--remove` takes out the link, the Nautilus item, the Strata action and both blocks, keeps Settings, the password and the history, and ends with `omarchy plugin remove sorydi3.kindle-send`. It never touches the plugin folder.
- [ ] `--purge` also removes `~/.config/kindle-send/` and `~/.local/state/kindle-send/` and runs `secret-tool clear service kindle-send`; `shell.json` is unchanged. The keyring is your session's, not the temp `HOME`'s: even there `--purge` deletes your real app password, so run it only when you mean to (or with a stub `secret-tool` first on `PATH`).

## 27. Plugin text from the English catalog (#65, spec §17 Translations)

All the plugin's own text comes from `i18n/en.json` through Omarchy's `Commons.Translations`; English should read exactly as before, apart from the fixed failure hints.

- [ ] Open the Picker, mark Books, `Tab` a Route, open Settings, save with a typo, `Ctrl+T`, send by email and USB, unplug the Kindle for a Pending Send: every line reads as before, and no raw key (`rows.marked`, `message.too_big_for_email`, …) shows anywhere, including the bar-widget tooltip and the notifications.
- [ ] **Live language switch.** Copy `i18n/en.json` to `i18n/da.json` in the plugin folder and change a few values (e.g. `keys.close`, `bar.idle`, `rows.marked`). Pick Dansk under Setup > Language: the Picker's footer and the bar-widget tooltip follow at once, with no shell restart; numbers show a decimal comma (`1,2 MB`). Switch back and delete `da.json`.
- [ ] **Unknown code.** A failure whose `code` the catalog lacks shows kindle-send's English `reason` (e.g. temporarily delete `message.kindle_full` from `en.json` and fill the Kindle).
- [ ] **Broken plugin folder.** Rename the plugin's `bin/kindle-send`: the Picker says "Couldn't run kindle-send." and names that path, a Send fails with "Couldn't run kindle-send from the plugin folder. Reinstall Books to Kindle." Neither mentions `scripts/install.sh`. "Couldn't list your Books" names the bundled path in its `plan --folders` hint. Put it back.
- [ ] **Plain text.** Name a Book `<b>bold</b>.epub` and `<img src="https://example.invalid/x">.pdf`: the Picker shows the names literally, with no bold and no image request.

## 28. README, LICENSE, a fresh install and moving the author's install (#67, spec §17)

`omarchy plugin validate .` at the root is automated (`tests/test_layout.py`); the README and LICENSE are pinned by `tests/test_readme.py`.

- [ ] **Fresh install from GitHub.** As a clean user (no `~/.config/kindle-send/`, no plugin folder), run `omarchy plugin add https://github.com/sorydi3/kindle-send --enable`. The book icon appears in the bar; a click opens the Picker straight into Settings. Fill them in with test addresses, `Ctrl+T`: the test Book reaches the Kindle. Nothing else was run.
- [ ] Follow the README top to bottom on that user: Install, the extras script, Configure, Use, Update, Remove. Every command works as written, every key does what the table says, and `--purge` plus `omarchy plugin remove sorydi3.kindle-send` leave only the `.before-kindle-send` backups.
- [ ] The README shows on GitHub with the not-affiliated line under the title, `docs/demo.gif` plays and the LICENSE is detected as MIT.
- [ ] **Moving the author's install** (spec §17). Check nothing is waiting for the Kindle. Point `~/.config/omarchy/plugins/sorydi3.kindle-send` at the checkout's root and remove `~/.local/share/kindle-send/`. Run `scripts/install.sh`: it offers to replace the old link and binding block; afterwards `~/.local/bin/kindle-send` points at the checkout's `bin/kindle-send` and `SUPER + SHIFT + K` says "Books to Kindle". Run `kindle-send` once: `~/.config/kindle-send/settings.json` holds the old Settings; the app password and the `~/.local/state/kindle-send/` history are unchanged. Restart the shell: the bar icon and the Picker work, and a Send goes out.

## 29. The preview image and the Picker's theme colours (#68, spec §17)

`preview.png` is rendered offscreen by `docs/preview/render.sh` (a throwaway HOME with demo Books and demo Settings, a stand-in `secret-tool`, the active theme copied read-only, the Picker's own QML and Omarchy's own notification card). `tests/test_layout.py` fails on a bare `Color.` in the plugin's QML.

- [ ] Run `docs/preview/render.sh /tmp/preview.png`: nothing shows on screen, the image shows the Picker with six demo Books (Email and USB, one marked, the footer) and a "Sent to Amazon. Should appear on your Kindle within a few minutes." card; no real address, Book or path appears. `~/.config/kindle-send/` and the keyring are untouched.
- [ ] Run `docs/preview/render-gif.sh /tmp/demo.gif` (the same throwaway world; `demo.qml` drives the real bar widget and Picker through a timeline, with a stand-in Service that sends nothing): nothing shows on screen, and the GIF, 1200 px wide and under 5 MB, loops through the bar click, a filter, two Books marked with one switched to USB, the "Sent 2 Books" card, Settings with the demo addresses and "Stored. Type to replace it.", and Esc twice. Each key caption shows as its key acts; no real address, Book or path appears.
- [ ] **Theme colours in the live Picker.** Open the Picker: the scrim, card, border, highlighted row and accent text use the theme's menu colours (they were QtQuick's `Color` under Qt 6.12, so every colour binding failed). Switch theme with the Picker closed and open it again: it follows.

## 30. Review fixes for publishing (#58)

- [ ] **Unreadable Settings file.** Back up `~/.config/kindle-send/settings.json`, then write `{ broken` into it. Open the Picker: it says "Couldn't list your Books." with "…/settings.json isn't valid JSON, so it wasn't changed." (not Settings titled "Set up Books to Kindle"); `Enter` tries again. `Ctrl+,`: the status line says the same. A Send by email fails with that line too. The file still holds `{ broken`. Put the backup back.
- [ ] **Someone else's Nautilus file.** In a temp `HOME`, put any other `~/.local/share/nautilus-python/extensions/kindle-send.py` there and run `scripts/install.sh --remove`: it says `… is not Books to Kindle's; left alone.` and the file is unchanged.
- [ ] **Bar widget clicks.** Middle-click and right-click on the icon do nothing; left-click toggles the Picker.
- [ ] **Language switch with Settings open.** With a `da.json` as in section 27, save Settings with a typo so a field problem and the status line show, then pick Dansk under Setup > Language: both change language at once, without saving again.
- [ ] **Test-send time.** `Ctrl+T` in Settings: "Gmail accepted the test Book at …" writes the time as the language picked under Setup > Language writes it (e.g. `9:05 AM` in English, `09.05` in Danish).

## 31. Security review fixes (marketplace review, spec §6, §7, §9, §12)

- [ ] **Gmail's certificate is checked.** A Send by email and a Settings save with a typed app password still work as before (the system's CAs trust Gmail).
- [ ] **A certificate Gmail can't prove is refused.** Serve a self-signed certificate on 127.0.0.1:465 (`sudo openssl s_server -accept 465 -cert self.pem -key self.key`) and add a temporary `127.0.0.1 smtp.gmail.com` line to `/etc/hosts`. A Send by email fails with "Couldn't verify Gmail's certificate: self-signed certificate." and `s_server` never prints an `AUTH` line; saving Settings with a typed app password says "Couldn't verify Gmail's certificate, so the password wasn't checked: self-signed certificate. Saved anyway." Remove the `/etc/hosts` line and stop `s_server`.
- [ ] **Private history.** `chmod 755 ~/.local/state/kindle-send; chmod 644 ~/.local/state/kindle-send/history.jsonl`, then send a Book: `stat -c '%a %n' ~/.local/state/kindle-send ~/.local/state/kindle-send/*` shows `700` for the folder and `600` for `history.jsonl` and `email-limit.json`. After a Settings save, `~/.config/kindle-send` is `700`.
- [ ] **No writes through links on the Kindle.** A Kindle's FAT file system can't hold links, so the link cases are covered by `tests/test_security.py` against a temp mount (a link left at `documents/.<name>.part` is left alone, never written through; a `documents` linking off the mount fails with "Couldn't copy to the Kindle: documents links outside the Kindle."). On the real Kindle, a USB Send still copies the Book into `documents/` and leaves no `.part` file.

## 32. Extras script review fixes (marketplace review, spec §14)

Run each in a temp `HOME` (e.g. `env HOME=$(mktemp -d) XDG_CONFIG_HOME= XDG_DATA_HOME= XDG_STATE_HOME= scripts/install.sh …`), never against your own (a changed Nautilus item still runs `nautilus -q`, closing open Nautilus windows); `tests/test_install.py` and `tests/test_strata_action.py` cover the same cases with stub tools.

- [ ] **Someone else's Nautilus file.** Put any other `~/.local/share/nautilus-python/extensions/kindle-send.py` there and run `scripts/install.sh` on a terminal, answering `y`: it says `… is not Books to Kindle's; left alone.`, never asks to add or update the Nautilus item, the file is unchanged and there is no `kindle-send.py.before-kindle-send`. Same with `--yes`.
- [ ] **An older Nautilus file of ours.** Put a `kindle-send.py` there holding `PLUGIN_ID = "sorydi3.kindle-send"` and anything else, run `scripts/install.sh --yes`: it says "Updated …. The previous one is kept as ….before-kindle-send.", the backup holds the old text, the new file matches `nautilus/kindle-send.py` with mode `644`, and no `.kindle-send.py.kindle-send-…` file is left in the folder.
- [ ] **Planted links are not written through.** With a `~/.config/hypr/bindings.lua` holding an `o.bind` line and a `~/.config/omarchy/extensions/omarchy-menu.jsonc`, make `echo mine > /tmp/victim` and link each of `bindings.lua.before-kindle-send`, `bindings.lua.kindle-send-tmp`, `omarchy-menu.jsonc.before-kindle-send`, `omarchy-menu.jsonc.kindle-send-tmp` and `~/.config/strata/actions/kindle-send/action.toml.kindle-send-tmp` to it, then run `scripts/install.sh --yes` and `--remove`: `/tmp/victim` still says `mine`, each `.before-kindle-send` is now a plain file holding the file as it was, and the binding and menu entries were added and then removed.
- [ ] **Re-run.** A second `scripts/install.sh --yes` says "Already" for each extra and changes no file.

## 33. USB copy review fixes (marketplace review, spec §7)

`tests/test_usb.py` covers both with a fake Kindle on a temp mount (unmounted, no longer a mount point, or another folder at its path during a Conversion; two Sends of one Book interleaved; another Send's staging file present).

- [ ] **Unplugged during a Conversion.** Plug in the Kindle and start a USB Send of a large EPUB. While it says "Converting", unmount the Kindle (`udisksctl unmount -b <partition>`, leaving the mount folder in place, or `sudo mkdir -p` it back). The Book becomes a Pending Send ("Kindle not plugged in"), never "copied"; the mount folder on the local disk is still empty (no `documents`). Mount the Kindle again: the pending Book is copied.
- [ ] **Two Sends of one Book at once.** With the Kindle plugged in, start a USB Send of the same large Book from the terminal (`kindle-send send --route usb <book>`) and from the Picker at the same time. Both say copied, `documents/` holds the Book once with its full size, and no `.<name>.….part` file is left.
