# Books to Kindle

Send the ebooks on your computer to your Kindle from the Omarchy shell: by email, or over USB when the Kindle is plugged in.

> Unofficial: send ebooks to your Kindle by email or USB. Not created or endorsed by Amazon.

![Books to Kindle: the bar icon opens the Picker; two Books are marked, one switched to USB, and sent; then Settings](docs/demo.gif)

- **A keyboard Picker.** Type to filter, `Space` to mark, `Enter` to send. It closes at once; progress comes as Omarchy notifications.
- **Email or USB, per Book.** It picks the Route for you: email when the format and size allow, USB otherwise. `Tab` switches it.
- **EPUB over USB.** Converted to AZW3 with Calibre on the way, original untouched.
- **Waits for your Kindle.** A USB Book with no Kindle plugged in waits, and goes out when you plug it in. The bar icon shows how many are waiting.
- **Stays under Amazon's limit.** Emails are paced so Amazon doesn't throttle you.
- **Right-click in Nautilus or Strata** (optional): "Send to Kindle" on any ebook.

## Requires

- Omarchy with omarchy-shell plugins.
- `python3` and `secret-tool` (libsecret), with GNOME Keyring running.
- A Gmail account with 2-Step Verification, for an app password.
- Optional: `calibre` (EPUB over USB), `nautilus-python` (Nautilus right-click), Strata (Strata right-click).
- Drive-style Kindles over USB (Paperwhite, Oasis and older). MTP Kindles (2024+, Scribe) can only use email.

## Install

```sh
omarchy plugin add https://github.com/sorydi3/kindle-send --enable
```

That is all you need. A book icon appears in the bar; click it to open the Picker. The first time, it opens straight into Settings.

**Optional extras**, asked about one by one: `kindle-send` in your terminal (a link in `~/.local/bin`), the Nautilus and Strata right-click entries, the `SUPER + SHIFT + K` binding and Omarchy menu entries. Run it in a terminal, so it can ask:

```sh
~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh
```

It backs up each config file before it edits it (`<file>.before-kindle-send`) and is safe to run again. `--yes` adds everything without asking; `--help` says more.

## Configure

The Picker's Settings (`Ctrl+,`, or the cog) ask for:

1. **Your Kindle's email address.** amazon.com → Manage Your Content and Devices → Devices.
2. **The Gmail address that sends the Books.** Add it to Amazon's Approved Personal Document Email List, or Amazon silently drops every Book.
3. **A Gmail app password.** Create one at myaccount.google.com/apppasswords. Saving checks it with Gmail.
4. **Book folders** the Picker lists (default `~/Books, ~/Downloads`).

Then `Ctrl+T` sends a test Book. Amazon never confirms delivery, so check your Kindle.

Settings live in `~/.config/kindle-send/settings.json`, so disabling or removing the plugin keeps them. With the extras, `kindle-send setup` asks the same questions in a terminal.

## Use

| Key | Does |
|---|---|
| `SUPER + SHIFT + K` | open the Picker (with the extras; or click the bar icon) |
| type | filter by file name |
| `Space` | mark a Book |
| `Tab` | switch its Route between Email and USB |
| `Enter` | send the marked Books, or the highlighted one |
| `Delete` | on "N Books waiting for Kindle": cancel them |
| `Ctrl+,` | Settings |
| `Esc` | clear the search, or close |

The plugin's text is in `i18n/en.json`. A translation is one more `i18n/<code>.json` file; missing keys fall back to English.

## Update

```sh
omarchy plugin update sorydi3.kindle-send
```

## Remove

```sh
~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh --remove   # if you added the extras
omarchy plugin remove sorydi3.kindle-send
```

That keeps your Settings, app password and Send history. To delete them too, run the extras script with `--purge` instead of `--remove`, or:

```sh
rm -r ~/.config/kindle-send ~/.local/state/kindle-send
secret-tool clear service kindle-send
```

The keyring belongs to your login session, so this deletes your real app password, wherever you run it.

The `.before-kindle-send` backups are never deleted; remove them by hand once you no longer need them. If you installed an early version, also remove `~/.local/share/kindle-send/`.

## Security

- The Gmail app password lives in GNOME Keyring. The Picker passes it to `kindle-send` on stdin only: never on a command line, in a log or in a settings file.
- The only network connection is to Gmail's mail server (`smtp.gmail.com`), when sending or checking the password.
- Like every Omarchy plugin, this runs unsandboxed inside omarchy-shell. Read the code before you install it.
- The extras script asks before every change and backs up each config file it edits.

## License

MIT. See [LICENSE](LICENSE).
