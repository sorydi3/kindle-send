# What exactly does Amazon accept by email to a Kindle address?

Type: research
Status: resolved
Blocked by: none
Parent: ../map.md

## Question

For the Email route as of late 2026: which file formats are accepted, the size limit per attachment and per email, how many attachments are allowed, whether subject lines like "convert" still matter (e.g. for PDFs), how Approved senders work, and what feedback Amazon sends on success and on failure. Also: is there any non-email upload path (Send to Kindle web/desktop) with a larger limit that a script could use?

## Answer

Full findings: branch `research/email-route`, file `research/email-route.md` (commit 5d445c5; never merged). amazon.com help returned 503, so pages were read from Amazon's mirror at `digprjsurvey.amazon.com` (same help node ids; canonical URLs in the file).

- Formats: PDF, EPUB, TXT, RTF, HTML, images, ZIP (unpacked); DOC/DOCX likely accepted. MOBI is being phased out. No password-protected files; under 8,000 pages.
- Limits: 50 MB per email (count it uncompressed), 25 attachments. Frequent sends get throttled, then suspended (E010-E012), so the plugin must rate-limit.
- With Gmail's ~25 MiB ceiling (see [How can a script send Gmail mail and keep the app password safe on this machine?](04-smtp-and-secrets-facts.md)), Gmail, not Amazon, sets the real Email route size limit.
- "convert" subject: undocumented now; harmless to add for PDFs.
- Approved senders: set under Manage Your Content and Devices > Preferences > Personal Document Settings. Must send through a real SMTP account (no From spoofing). Amazon may ask for a 48-hour verification click.
- Feedback: no documented success email; failures come back as error codes E001-E016/E999, but to which address is undocumented.
- Non-email: Send to Kindle for Web (200 MB) has no public API; desktop app is Mac/Windows only. Email is the only scriptable route.
- Open, settle by testing: DOCX, ZIP over 50 MB, effect of "convert", where failure notices land.
