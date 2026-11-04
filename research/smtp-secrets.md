# Sending a large attachment via Gmail SMTP, and storing the app password

Research for ticket `.scratch/kindle-send/issues/04-smtp-and-secrets-facts.md`.
Researched 2026-11-04 on this machine (Omarchy, kernel 7.2.8, python 3.14.8, curl 8.23.0, quickshell 0.3.2).

## TL;DR

- **Use Python `smtplib` + `email.message.EmailMessage`.** It's installed, it builds the MIME message and base64 for you, and it can check Gmail's advertised `SIZE` before sending. curl can also work (`-F` builds MIME). msmtp isn't installed and doesn't build MIME, so it only adds value as a sendmail-style relay.
- **Size budget:** Gmail allows **25 MB of attachments** for personal accounts. On the wire, `smtp.gmail.com` advertises `SIZE 35882577` bytes (observed). base64 adds about 37% (4/3 plus CRLF every 76 chars), so a raw file larger than **about 25 MiB (~26 MB) will be rejected**. Treat ~25 MB raw as the hard ceiling and check the encoded size before sending.
- **App passwords** still exist (Nov 2026) for personal accounts. They require 2-Step Verification. They're unavailable with Advanced Protection, with security-key-only 2SV, or on work/school accounts, and they're revoked when the account password changes.
- **Secret store:** `secret-tool` (libsecret) is installed, and **gnome-keyring is already running as the Secret Service** (`org.freedesktop.secrets`), with an unlocked default collection. That's the zero-install option. `pass`, `keepassxc` and `msmtp` are one `pacman -S` away in `extra`.

## 1. Gmail facts

| Fact | Value | Source |
|---|---|---|
| Attachment limit (personal Gmail) | "25 MB". Over the limit, Gmail web swaps the file for a Drive link (UI only; over SMTP the message is rejected) | [Gmail Help: Attachments](https://support.google.com/mail/answer/6584?hl=en) |
| SMTP host / ports | `smtp.gmail.com`, 465 (SSL) or 587 (TLS/STARTTLS). Username is the full address, password is the app password | [Workspace Admin: Send email from a printer, scanner, or app](https://knowledge.workspace.google.com/admin/gmail/send-email-from-a-printer-scanner-or-app?hl=en) |
| Daily sending limit via smtp.gmail.com | 2,000 messages/day (Workspace figure on the same page) | same |
| Advertised SMTP max message size | `SIZE 35882577` (≈34.2 MiB), observed via EHLO on 2026-11-04, both before and after STARTTLS. Also advertised: `AUTH LOGIN PLAIN XOAUTH2 …`, `8BITMIME`, `CHUNKING` | Live probe (`smtplib.SMTP('smtp.gmail.com',587).ehlo()`); SIZE semantics: [RFC 1870](https://www.rfc-editor.org/rfc/rfc1870) |
| Encoding counts toward limits | Google states for Workspace receiving limits that sizes are "the limit after encoding" and that encoding adds roughly 37% | [Workspace Admin: Gmail receiving limits](https://knowledge.workspace.google.com/admin/gmail/gmail-receiving-limits-in-google-workspace?hl=en) |
| base64 overhead | 3 bytes become 4 chars, and lines are at most 76 chars (+CRLF), so ×4/3×78/76 ≈ **1.37** | [RFC 2045 §6.8](https://www.rfc-editor.org/rfc/rfc2045#section-6.8) |

**Arithmetic (inference):** 35,882,577 / 1.37 ≈ 26.19 MB ≈ 24.98 MiB. The advertised SIZE is almost exactly 25 MiB × 1.37, so the "25 MB" UI limit is enforced as roughly 25 MiB of *raw* attachment after encoding. In practice: a raw EPUB/PDF up to ~25 MB fits, and anything over ~26 MB gets a 552 from the server. Kindle's Send-to-Kindle email has its own limit, which other research covers. The binding constraint is whichever is lower.

**Third-party sources disagree.** Some blogs claim "~18 MB usable" (assuming 25 MB *encoded*). The observed SIZE value contradicts that for personal Gmail over SMTP. Trust the EHLO value, and have the script read it at runtime rather than hard-coding it.

## 2. App passwords: status as of late 2026

From [Google Account Help: Sign in with app passwords](https://support.google.com/mail/answer/185833?hl=en) (fetched 2026-11-04):

- An app password is "a 16-digit passcode that gives a less secure app or device permission to access your Google Account."
- **2-Step Verification must be on** to create one.
- The option is missing if 2SV is set up with **security keys only**, if it's a **work/school/organization** account, or if **Advanced Protection** is on.
- **Changing the account password revokes all app passwords.**
- Google calls them "not recommended and … unnecessary in most cases" and prefers Sign in with Google. The page gives no removal date.

Related: [Less secure apps & your Google Account](https://support.google.com/accounts/answer/6010255?hl=en). Plain username/password sign-in ("less secure apps") ended for **Workspace** accounts starting January 2025. App passwords (with 2SV) are the remaining non-OAuth route for personal accounts. The EHLO above still advertises `AUTH PLAIN LOGIN`, which is what an app password uses.

## 3. Sending options compared

| | Python `smtplib` | curl SMTP | msmtp |
|---|---|---|---|
| Installed? | yes (python 3.14.8) | yes (8.23.0, OpenSSL) | **no** (`extra/msmtp 1.8.34`) |
| Builds MIME + base64 attachment | yes (`EmailMessage.add_attachment`, base64 by default via `email.contentmanager`) | yes, `-F` "composes a multipart mail message" for SMTP and supports `encoder=base64` | **no**. "Msmtp transmits mails unaltered", so it needs a pre-built message |
| TLS | `SMTP_SSL(host,465)` or `SMTP(...,587).starttls()` | `smtps://smtp.gmail.com:465` or `smtp://…:587 --ssl-reqd` | `tls on`, `tls_starttls on/off` |
| Password without argv exposure | read from stdin / subprocess (`secret-tool lookup …`) | `--netrc-file`, `-K -` config on stdin (`user = "a:b"`), or `--variable pw@-` | `passwordeval "secret-tool lookup …"` (built-in keyring support) |
| Pre-flight size check | `s.esmtp_features['size']` after `ehlo()` | none (server rejects at end of DATA) | none |
| Error reporting | Python exceptions (`SMTPAuthenticationError`, `SMTPDataError` 552…) | exit code + `-v` transcript | exit code (sysexits) |

Sources: [smtplib docs](https://docs.python.org/3/library/smtplib.html), [email.message docs](https://docs.python.org/3/library/email.message.html), [email.contentmanager docs](https://docs.python.org/3/library/email.contentmanager.html), [curl man page (`-F`, `--config`, `--variable`)](https://curl.se/docs/manpage.html), [Everything curl: SMTP](https://everything.curl.dev/usingcurl/smtp.html), [msmtp manual](https://marlam.de/msmtp/msmtp.html).

**Recommendation:** Python. It needs no install, makes the size check trivial, and gives clear errors. Sketch (not run; no secrets were stored):

```python
import smtplib, ssl, subprocess, sys
from email.message import EmailMessage
pw = subprocess.run(["secret-tool","lookup","service","kindle-send","user",FROM],
                    capture_output=True, text=True, check=True).stdout.rstrip("\n")
msg = EmailMessage(); msg["From"]=FROM; msg["To"]=KINDLE; msg["Subject"]="doc"
msg.set_content("")
msg.add_attachment(open(path,"rb").read(), maintype="application",
                   subtype="epub+zip", filename=name)
raw = msg.as_bytes()
with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as s:
    s.starttls(context=ssl.create_default_context()); s.ehlo()
    if len(raw) > int(s.esmtp_features.get("size", 0) or 1<<62): sys.exit("too big")
    s.login(FROM, pw); s.send_message(msg)
```

curl equivalent (attachment via `-F`, credentials via a config on stdin so they never appear in `ps`):

```sh
printf 'user = "%s:%s"\n' "$FROM" "$(secret-tool lookup service kindle-send user "$FROM")" |
curl -sS --ssl-reqd smtp://smtp.gmail.com:587 -K - \
  --mail-from "$FROM" --mail-rcpt "$KINDLE" \
  -H "Subject: doc" -H "From: $FROM" -H "To: $KINDLE" \
  -F '=;type=text/plain' -F "=@$FILE;encoder=base64"
```

## 4. Secret stores on this machine

Checked with `pacman -Q`, `command -v`, `pacman -Si`, `busctl --user list`:

| Store | Status here | Install |
|---|---|---|
| libsecret / `secret-tool` | **installed** (libsecret 0.21.8.2) | n/a |
| gnome-keyring | **installed and running**: `gnome-keyring-daemon` (pid 966) owns `org.freedesktop.secrets` on the user bus. Collections: `session`, `Default_5fkeyring` (default alias → `Default_keyring`), **Locked = false**. PAM hooks in `/etc/pam.d/sddm{,-autologin}` | n/a |
| KWallet | **installed** (kwallet 6.31, `kwalletd6`, `kwallet-query`); only *activatable* on D-Bus (`org.kde.kwalletd6`, `org.kde.secretservicecompat`), not running | n/a |
| pass | not installed | `pacman -S pass` (extra 1.7.4); needs a GPG key (`gpg` is installed) |
| KeePassXC | not installed | `pacman -S keepassxc` (extra 2.7.12) |
| msmtp | not installed | `pacman -S msmtp` (extra 1.8.34) |
| chmod-600 file | always available | n/a |

### How each is read (shell script, or QML via `Quickshell.Io.Process`)

Quickshell's `Process` takes `command` as a list of strings and "does not run command in a shell" (use `["sh","-c",…]` if needed). Read stdout with `StdioCollector`/`SplitParser`, and check `exited(exitCode, exitStatus)`. Source: [Quickshell Process docs](https://quickshell.org/docs/v0.2.0/types/Quickshell.Io/Process/). QML has no native Secret Service binding, so every option below reduces to "run a CLI, read stdout." **Better design:** the QML service never touches the secret. It spawns the send script, and the script fetches the password itself. That keeps the password out of QML memory and logs.

- **secret-tool (gnome-keyring)**: `secret-tool lookup service kindle-send user me@gmail.com` prints the secret (adds a newline only on a tty). Store once with `secret-tool store --label='kindle-send Gmail' service kindle-send user me@gmail.com`, which prompts or reads stdin. If the collection is locked, lookup triggers an unlock prompt via `org.gnome.keyring.SystemPrompter`. QML: `command: ["secret-tool","lookup","service","kindle-send","user",addr]`. Python can also call it via subprocess (the `secretstorage` module is not installed). Source: `man secret-tool` (libsecret 0.21.8), [libsecret docs](https://gnome.pages.gitlab.gnome.org/libsecret/).
- **KWallet**: `kwallet-query -f <folder> -r <entry> kdewallet` (also `-l` to list, `-w` to write from stdin; from `kwallet-query --help`). It starts kwalletd6 on demand and may pop a KDE unlock dialog. Its `secretservicecompat` would conflict with gnome-keyring for the `org.freedesktop.secrets` name, so leave it alone. Using it adds little here.
- **pass**: `pass show kindle-send/gmail | head -n1`. Files are GPG-encrypted under `~/.password-store`, and decryption goes through gpg-agent/pinentry (a prompt when the agent cache is cold). Source: [pass(1)](https://git.zx2c4.com/password-store/about/).
- **KeePassXC**: either `keepassxc-cli show -s -a Password db.kdbx kindle-send/gmail` (prompts for the DB password, or uses `-k keyfile` / `--no-password`), which is awkward unattended. Or enable its Secret Service integration and keep using `secret-tool`. But "only one secret service provider can be enabled at a time" and you "may have to disable … GNOME Keyring or KWallet." Sources: [keepassxc-cli(1)](https://github.com/keepassxreboot/keepassxc/blob/develop/docs/man/keepassxc-cli.1.adoc), [KeePassXC Secret Service doc](https://github.com/keepassxreboot/keepassxc/blob/develop/docs/topics/SecretService.adoc).
- **chmod 600 file**, e.g. `~/.config/kindle-send/app-password` (mode 0600, dir 0700): `cat` it, or QML `FileView`. It's plaintext at rest and in backups, so only use it as a fallback.

**Recommendation:** `secret-tool` + the already-running gnome-keyring. No install, it's unlocked at login via PAM, it has a one-line lookup usable from both bash and Quickshell `Process`, and msmtp's `passwordeval` speaks it natively if msmtp is ever adopted.

## Open questions / not verified

- Not tested end-to-end (no app password exists or was stored). Actual 552 behaviour at ~26 MB is inferred from the advertised SIZE.
- The 1.37 factor ignores MIME headers/boundaries (a few hundred bytes), which is negligible.
- Kindle's own email-size limit is out of scope here (see the email-route research).
