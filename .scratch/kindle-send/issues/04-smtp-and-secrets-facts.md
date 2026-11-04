# How can a script send Gmail mail and keep the app password safe on this machine?

Type: research
Status: resolved
Blocked by: none
Parent: ../map.md

## Question

Without a full mail client: compare the options for sending a large attachment through Gmail SMTP with an app password (Python `smtplib`, `curl` SMTP, `msmtp`), including Gmail's own attachment limit. Then: which secret stores are available or easy to install on this Omarchy machine (`secret-tool`/GNOME Keyring, `pass`, KeePassXC, a permission-restricted file) and how a QML service or shell script reads from each.

## Answer

Full findings: branch `research/smtp-secrets`, file `research/smtp-secrets.md` (commit 27b5bff; never merged). Not tested end to end.

- Python `smtplib` + `EmailMessage.add_attachment` is the best fit (installed, encodes attachments, can read the server's size limit). `curl` works too; `msmtp` adds little.
- `smtp.gmail.com` port 465 (SSL) or 587 (STARTTLS); user = full address, password = app password.
- Size: Gmail allows 25 MB of attachments; the server advertised 35,882,577 bytes after encoding. base64 adds about 37%, so the practical raw ceiling is about 25 MiB. Read the limit at runtime instead of hard-coding it.
- App passwords still work for personal accounts with 2-Step Verification (not with Advanced Protection or work accounts); changing the account password revokes them.
- gnome-keyring is already running as the Secret Service and unlocks at login; `secret-tool` is installed. Nothing to install.
- Suggested shape: the QML service starts the send script, and the script fetches the password itself with `secret-tool lookup`, so the secret never passes through QML.
