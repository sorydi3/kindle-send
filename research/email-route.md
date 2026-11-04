# Email route: what Amazon accepts by Send to Kindle email

Research for ticket `.scratch/kindle-send/issues/01-email-route-facts.md`. Gathered 2026-11-04.

## Sources and how they were read

`www.amazon.com/gp/help/...` returned HTTP 503 to the fetch tool, so the Amazon help pages were read from Amazon's own help mirror at `digprjsurvey.amazon.com/csad/help/node/<nodeId>`. The node IDs are the same as on amazon.com, so the canonical URL is `https://www.amazon.com/gp/help/customer/display.html?nodeId=<nodeId>`. None of these pages shows a date.

| Tag | Page | Mirror URL read |
|---|---|---|
| [A1] | Learn How to Use Your Send to Kindle Email Address | https://digprjsurvey.amazon.com/csad/help/node/G7NECT4B4ZWHQ8WV |
| [A2] | Learn About Sending Documents to Your Kindle Library | https://digprjsurvey.amazon.com/csad/help/node/G5WYD9SAF7PGXRNA |
| [A3] | Troubleshoot Send to Kindle Errors | https://digprjsurvey.amazon.com/csad/help/node/T48rsVm3gY7KeGkKUk |
| [A4] | Add an Email Address to Receive Documents in Your Kindle Library | https://digprjsurvey.amazon.com/csad/help/node/GX9XLEVV8G4DB28H |
| [A5] | Learn About Two-Factor Authentication for Your Kindle Library | https://digprjsurvey.amazon.com/csad/help/node/G98WYFZBRHWGZACA |

Secondary sources (not Amazon) are marked **[secondary]** where they are used.

## Accepted file formats

[A2] lists these supported types:
HTML (.HTML, .HTM), RTF (.RTF), Text (.TXT), JPEG (.JPEG, .JPG), GIF (.GIF), PNG (.PNG), BMP (.BMP), PDF (.PDF), EPUB (.EPUB).

- **Word (.DOC/.DOCX):** not in the [A2] list as fetched. But error E003 in [A3] says Word files are accepted if they are ".DOC" or ".DOCX" and made with MS Word 97 or newer. **Treat Word as accepted but not advertised.** Test it before relying on it.
- **MOBI/AZW:** not in the list. MOBI/AZW are being phased out of Send to Kindle starting late 2022 **[secondary]** (https://www.inverse.com/input/tech/amazon-kindle-epub-file-support-kf8-ebooks). [A3] still has error E002 "Invalid or Corrupted MOBI File". **Use EPUB, not MOBI.**
- **ZIP:** accepted. "The conversion service automatically opens the ZIP files and converts them to the Kindle format." [A1]
- **Rejected:** password-protected or encrypted files (E004), and encrypted or corrupted PDFs (E005) [A3].
- **Page cap:** keep documents under 8,000 pages (E013/E016) [A3].

## Size limits

- **Per attachment: 50 MB, measured before compression.** E007 says "each attachment does not exceed 50 MB in size (before compression if zipped)" [A3].
- **Per email: 50 MB total.** "Send a total size of 50 MB or less." [A1]
- **Conflict on ZIP:** [A1] also says "Compress your documents into a ZIP file to send more than 50 MB." [A3]'s "before compression" wording seems to cancel that out. **For a script, the safe rule is ≤ 50 MB uncompressed per file and ≤ 50 MB per email.** Do not count on ZIP to get past the limit. Note too that many mail providers (e.g. Gmail) cap outgoing mail at about 25 MB, which is below Amazon's limit **[secondary]**.

## Attachment and recipient counts

- **Attachments:** at most 25 per email. "Send up to 25 attachments in one email." [A1] Error E006 is "Attachment Count Limit Exceeded" [A3].
- **Recipients:** at most 15 per email (E008 "Recipient Limit Exceeded") [A3].
- **[A1]'s "15" is about approved senders:** "Send to your Send to Kindle email from up to 15 approved email addresses." This is a different limit from the E008 recipient limit. [A4] gives no limit on the size of the approved list.
- **No attachment:** an email with no attachment fails with E009 [A3].
- **Throttling:** sending too many emails triggers E010 (warning), then E011 (final warning), then E012 (suspension for "suspected violation of our Send to Kindle Terms of Use") [A3]. **A script must rate-limit its sends.**

## Subject line / "convert"

- **No current Amazon page mentions the subject line or "convert".** [A1], [A2] and [A3] were all checked.
- **The convention has been around for years:** old Kindle user guides **[secondary]** (https://www.manualslib.com/manual/408654/Amazon-Kindle.html?page=132) and 2025–26 third-party guides **[secondary]** (e.g. https://smallpdf.com/blog/how-to-receive-pdfs-sent-via-email-on-kindle) say "convert" in the subject reflows a PDF into Kindle format, and a blank subject keeps the PDF in fixed layout.
- **What [A3] does say:** conversion can fail, and the fallback is visible. E016 "Original Layout Delivery" means the file "was delivered with its original layout preserved", and "Text size and text reflow are not adjustable for this document". E013 means it was delivered without newer features such as Scribe.
- **Conclusion:** "convert" is an undocumented convention that third parties say still works. Amazon does not commit to it. **Sending a PDF with "convert" is harmless.** If conversion fails, Amazon reports E016 instead of rejecting the file. **Sending EPUB avoids the question.**

## Approved senders

- **Only listed senders get through:** documents are delivered only from addresses on the *Approved Personal Document Email List* [A4].
- **How to add a sender:** Manage Your Content and Devices (https://www.amazon.com/mycd) → Preferences → Personal Document Settings → Approved Personal Document Email List → "Add a new e-mail address" [A4].
- **Unapproved sender:** fails with E014, "the document(s) sent to you will not be delivered to your Kindle". The notice is sent only once ("you will receive this notification only once") [A3].
- **Verification step (Amazon calls it two-factor authentication):** even an approved sender can trigger it. "When you send a document to your Send to Kindle email address … you receive an email asking you to verify your request within 48 hours." [A5]
  - **To avoid it,** make the Send to Kindle address "sufficiently secure": different from your other addresses, mixed upper/lower case and digits, and no personal information [A5].
- **Sender authentication checks [secondary]:** Amazon checks whether the sending server is allowed to send for the From domain (SPF-style). Spoofed or made-up From addresses get a verification email sent to that address, so they fail. A sender address that looks too much like the Kindle address also triggers verification (FiveFilters, 2021: https://www.fivefilters.org/?p=3272).
- **Implication for a script:** send through a real SMTP account whose domain authorizes the server (e.g. the user's own Gmail with an app password). Do not spoof the From address.

## Feedback Amazon sends

- **Success:** no Amazon page documents a success or delivery confirmation email. **Do not design around one.** Delivery is "attempted for up to 60 days" [A1], so a document may arrive late.
- **Failure:** [A3] defines error codes E001–E016 and E999 that users receive when something goes wrong:
  - unsupported format (E001), bad MOBI (E002), bad Word (E003), password-protected (E004), bad PDF (E005)
  - too many attachments (E006), too large (E007), too many recipients (E008), no attachment (E009)
  - throttling (E010–E012)
  - delivered without newer features (E013), unapproved sender (E014), web extraction failure (E015), delivered in original layout (E016)
  - internal error or maintenance (E999)

  [A3] does not say whether these notices go to the sender or to the account owner. FiveFilters reports **[secondary]** that verification mails go to the From address.
- **Verification:** the 48-hour verification email [A5] is the other feedback message.
- **For a script:** a send can only be confirmed out-of-band, by checking the library or device. The script can parse incoming mail for "E0xx" codes if it has access to that inbox.

## Non-email upload paths

From [A2]:

| Path | Limit | Linux script? |
|---|---|---|
| **Send to Kindle for Web** (https://www.amazon.com/sendtokindle) | "Upload documents (200 MB or smaller)" | Works in any browser, including on Linux, but needs a signed-in Amazon session. There is no public API. Scripting it means browser automation against a logged-in session, which is fragile and possibly against the Send to Kindle Terms of Use (https://www.amazon.com/sendtokindleterms, not reviewed). |
| Send to Kindle desktop app | No limit stated by Amazon. 50 MB per document **[secondary]** (https://blog.the-ebook-reader.com/2022/12/20/send-to-kindle-apps-for-pc-and-mac-now-support-epub/, https://www.takecontrolbooks.com/your-kindle-can-finally-read-epub-files/) | No: "the Send to Kindle app for Mac and Windows" only. |
| Kindle app for iOS/Android (share sheet) | Not stated | No. |
| Chrome extension | Web articles only | No (not a file upload path). |

**Bottom line:** the only path with a larger limit is the 200 MB web uploader. It is browser-only and authenticated, with no API, so it suits a manual fallback for big files. It is not a clean scripted route. The email route (≤ 50 MB, ≤ 25 files) is the only one a Linux script can officially use.

## Open questions / to verify by test

- Are DOCX files still accepted by email, given they are missing from the [A2] list? (E003 suggests yes.)
- Does a ZIP whose contents total over 50 MB uncompressed actually get through? [A1] and [A3] disagree.
- Does "convert" in the subject still change how a PDF is handled?
- Which address receives E0xx failure notices: the sender or the account email?
