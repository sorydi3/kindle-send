# Product

<!-- impeccable:product-schema 1 -->

## Platform

omarchy-shell

A native Linux desktop plugin, not web, iOS or Android: Quickshell/QML panels inside omarchy-shell on Hyprland, plus a nautilus-python extension, a Strata action and a Python CLI. Native expectations here are Omarchy's own menus, keybindings and `omarchy-notification-send` notifications.

## Users

Omarchy users who keep ebooks on their disk and own a Kindle. They are keyboard-first desktop users who want a Book on the Kindle without opening a browser, Amazon's apps or Calibre's UI.

The plugin is published for other Omarchy users as **Books to Kindle** (spec §17): installed with `omarchy plugin add` and listed on plugins.omarchy.org. First-run, setup and failure messages must make sense to a stranger, and nothing may assume the author's machine, Kindle model or folders.

## Product Purpose

Send local ebook files to one Kindle, by email (Gmail SMTP) or over USB, from the place the user already is: a keyboard picker, a file manager right-click, or the terminal. Success is a Book on the Kindle with no manual format juggling, and a clear reason when it can't get there.

## Positioning

It lives in the desktop shell itself. The Picker, notifications and right-click entries are omarchy-shell and file-manager native, and it chooses the Route per Book (email when the format and size allow, otherwise USB with EPUB-to-AZW3 Conversion), holds Books until a Kindle is plugged in, and paces emails under Amazon's unpublished throttle.

## Operating Context

- **Main path:** `SUPER + SHIFT + K` opens the Picker; type to filter, `Space` marks, `Tab` switches Route, `Enter` sends and closes at once. Keyboard speed matters most (confirmed as the user's daily path).
- **Other ways in:** Nautilus or Strata right-click "Send to Kindle" opens the Picker with those files marked; the `kindle-send` command; the Omarchy menu.
- **Feedback** happens after the Picker closes, entirely through Omarchy notifications updated in place (spec §10). The notification server draws no buttons; clicking is the only action.
- **Settings and setup** happen inside the Picker: one form opened with `Ctrl+,`, and on its own while setup is needed (spec §9). `kindle-send setup` in a terminal stays as the fallback.
- Vocabulary is fixed in `GLOSSARY.md` (Book, Route, Send, Pending Send, Email limit, Send limit, Send history, Book folders, Conversion). UI copy uses these terms.

## Capabilities and Constraints

- Full behavior and failure copy live in `docs/spec.md`; the decisions behind it are in issue #1.
- Two Routes only, one Kindle address, local files only. Unsupported formats and MTP Kindles are out of scope.
- Amazon never confirms delivery, so email success means "Gmail accepted it" and copy must not claim more.
- The Picker never sees the app password; secrets stay in GNOME Keyring.
- Pending Sends and Books held by the Send limit live in memory and are lost on a shell restart.
- `kindle-send` is Python standard library only; Calibre is optional.

## Brand Commitments

- Name: "Books to Kindle" (plugin id `sorydi3.kindle-send`). Unofficial: not created or endorsed by Amazon; no Amazon logos or artwork.
- The Picker always follows the active Omarchy theme: it uses only omarchy-shell's theme tokens (`Color.menu.*`, `Style.*`) and has no colors or fonts of its own. It must look native in every Omarchy theme. (Confirmed binding, 2026-11-09.)
- Voice: short, plain sentences that say what happened and what to do next ("Too big for email (N MB). Switch it to USB."). See spec §10 and §13.

## Evidence on Hand

- `docs/spec.md`, `GLOSSARY.md`, `docs/manual-checks.md`, and the test suite in `tests/`.
- `assets/test.epub`, the setup test Book.
- No screenshots, users, testimonials or install counts exist. Do not invent any.

## Product Principles

1. **Native first.** Look and behave like part of Omarchy: its theme, its keys, its notifications. Never a separate app.
2. **The keyboard path is the fast path.** Open, filter, send, gone. Nothing should slow down `SUPER + SHIFT + K` → `Enter`.
3. **Say what actually happened.** Report what the plugin knows (accepted by Gmail, copied, waiting) and never claim delivery it can't confirm.
4. **Every failure names its fix.** A reason plus the next step, and a click into setup when setup is the fix.
5. **Works for someone who isn't the author.** No assumptions about one machine, one Kindle model or one set of folders.
