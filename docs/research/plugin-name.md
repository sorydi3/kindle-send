# Research: can the plugin be called "Send to Kindle"?

Ticket: [#49](https://github.com/sorydi3/kindle-send/issues/49) (map [#46](https://github.com/sorydi3/kindle-send/issues/46)). Researched 2026-11-13.

**This is not legal advice.** It sets out what Amazon publishes and what similar tools do. The recommendation at the end is labelled as one.

## Short answer

- **"Send to Kindle" is the name of Amazon's own product.** Amazon uses it for the `@kindle.com` email service, its web uploader, its old PC/Mac apps and its official Chrome extension, "Send to Kindle for Google Chrome™". If the plugin uses exactly that name, a user will reasonably think it is Amazon's. That is the thing every Amazon guideline below forbids.
- **What Amazon allows** for third-party software is naming Kindle only to say what the software is *for*, using words like "for" or "to", with no Amazon logo, no implied endorsement, and a "not created or endorsed by Amazon" statement. Its affiliate guidelines go further and ban the mark in any "application, plug-in or other software name". Those affiliate guidelines bind affiliates only, but they show how Amazon reads the mark.
- **Common practice:** most open-source senders put "Kindle" in a descriptive name that is not Amazon's product name (`kindle-send`, `sendKindle`, `ksend`, "Push to Kindle", KindleEar), and the careful ones add an "unofficial / not affiliated with Amazon" line. A few use "Send to Kindle" as is. No takedown or forced rename over the Kindle mark turned up.
- **Recommendation:** rename the display name away from Amazon's exact product name, keep "Kindle" in it as a "for"/"to" descriptor, add an "unofficial, not affiliated with Amazon" statement, and keep the id `sorydi3.kindle-send`. See [Recommendation](#recommendation).

## 1. What Amazon publishes

Amazon has no single public "Kindle brand guidelines" page for independent software. The relevant rules are spread over several program pages. Each one formally binds only the members of its program (app developers, affiliates, KDP publishers), but together they show consistently how Amazon wants its marks used.

### Amazon Appstore developer trademark guidelines (closest match)

[Trademark Use and Branding Guidelines, Amazon Developer](https://developer.amazon.com/support/legal/tuabg), section "Using an Amazon Name in the Title of Your Mobile App":

> If you refer to Amazon or any Amazon product or service (including "Kindle" or "Fire tablet") in the title of your app, you must:
> 1. Refer to Amazon or the Amazon product or service only in a way that describes the app's compatibility or purpose, using words like "for" or "to." (e.g., "Tips and Tricks for Fire tablets")
> 2. Not include any Amazon logo, icon, or image in the icons for your app
> 3. Not imply any sponsorship or endorsement by Amazon or otherwise mischaracterize your relationship with Amazon
> 4. Include the following statement in the product description for your mobile app: "This app was not created or endorsed by Amazon."

The same page says not to use Amazon marks in a way that "implies sponsorship or endorsement by Amazon", and that each mark must appear "by itself, with reasonable spacing" and must not be altered.

This is the one Amazon text written for software that names Kindle. Strictly, "Send to Kindle" already has the "to" shape (rule 1). But it is also word for word the name of Amazon's own product, so under rule 3 users could take the plugin for Amazon's.

### Amazon Associates (affiliate) trademark guidelines (strictest)

[Associates Program, Trademark Guidelines](https://affiliate-program.amazon.com/help/operating/amazonmarks/), section 7:

> You are not allowed to use any trademark of Amazon or its affiliates, or a variant or misspelling of a trademark … (c) In any application, plug-in or other software name … e.g. "Kindle Book Shop" …

Section 7 also bans Kindle in domain names (examples: `kindlemagazines.mydomain.info`, `kindlewirelessreader.co.uk`) and in social-media usernames ("Kindle For You"). Section 2 bans use "that implies sponsorship or endorsement by us". These rules bind affiliates, and this plugin is not one. They are the strictest reading of the mark Amazon has published.

### Other Amazon pages

- [Amazon trademark usage guidelines (Help node GNYNL3A8HPATWCH8)](https://digprjsurvey.amazon.com/csad/help/node/GNYNL3A8HPATWCH8): "You may not use the Marks in any manner that implies sponsorship or endorsement by Amazon" and "You may use the Marks solely for the purpose expressly authorized by Amazon."
- [KDP badge guidelines](https://kdp.amazon.com/en_US/help/topic/G9WES4WJAC3GUVSV): these cover only the "Available at Amazon"/Kindle badges, not software names.
- The Alexa/Echo [trademark guidelines](https://developer.amazon.com/en-US/alexa/branding/alexa-guidelines/trademark-guidelines) say not to use a mark as a verb or a pun. Amazon's general contact for questions is `trademarks@amazon.com`.

### The marks themselves

- **KINDLE** is a registered US word mark of Amazon Technologies, Inc. (for example Serial 77916414, Reg. 4380471, classes 9, 35 and 42; [record](https://trademarkdir.com/trademark/kindle-77916414)).
- I found no separate registration for the phrase "SEND TO KINDLE" (a search turned up none; not checked directly in USPTO TSDR). It does not need one to matter: it is the name Amazon uses for its product, and it contains the registered KINDLE mark.
- Amazon's own use of the name: the official Chrome Web Store extension is titled ["Send to Kindle for Google Chrome™"](https://chromewebstore.google.com/detail/send-to-kindle-for-google/cgdjpilhipecahhcilnafpblkieebhea), and Amazon brands its web uploader and email service as Send to Kindle (amazon.com/sendtokindle). This repo's own `docs/spec.md` already calls the web uploader `Amazon's "Send to Kindle for Web"`.

## 2. How comparable tools name themselves

Star counts are from GitHub on 2026-11-13. Disclaimers are quoted from each project's README.

| Project | Name it uses | Disclaimer |
|---|---|---|
| [nikhil1raghav/kindle-send](https://github.com/nikhil1raghav/kindle-send) (Go CLI, 281★) | `kindle-send`, the same as this repo's command | none |
| [kparal/sendKindle](https://github.com/kparal/sendKindle) | `sendKindle`, "CLI tool for sending files via email to your Amazon Kindle device" | none |
| [annnhan/ksend](https://github.com/annnhan/ksend) | `ksend` | none |
| [cdhigh/KindleEar](https://github.com/cdhigh/KindleEar) (2.9k★) | KindleEar | none |
| [ciromattia/kcc](https://github.com/ciromattia/kcc) (6k★) | "KCC (a.k.a. Kindle Comic Converter)" | "**KCC** _is not_ Amazon's Kindle Comic Creator nor is in any way endorsed by Amazon." |
| [jooray/kindbeamer](https://github.com/jooray/kindbeamer) | KindBeamer, "unofficial, open-source replacement for Amazon's *Send to Kindle* desktop app" | "this project is not affiliated with, endorsed by, or sponsored by Amazon." |
| [FiveFilters Push to Kindle](https://help.fivefilters.org/push-to-kindle/) (browser extensions, iOS app) | "Push to Kindle" (the Firefox add-on slug is still `kindle-it`, an older name). On iOS it is listed as **"Push for Kindle"**: FiveFilters [says](https://www.fivefilters.org/?p=3281) Apple's naming rules stopped them using "Push to Kindle" | — |
| [bookfere/Send-to-Kindle-Calibre-Plugin](https://github.com/bookfere/Send-to-Kindle-Calibre-Plugin) (160★) | "Send To Kindle Calibre Plugin", toolbar button "Send to Kindle" | none |
| [GabrielRF/Send2KindleBot](https://github.com/GabrielRF/Send2KindleBot) | "Send2KindleBot", "Send to Kindle Telegram Bot" | none |
| [miracle2k/sendtokindle](https://github.com/miracle2k/sendtokindle) | "Graphical Send to Kindle Utility for Ubuntu" | none |
| [Raycast "Send to Kindle"](https://www.raycast.com/lemikeone/send-to-kindle) (third-party store extension) | "Send to Kindle" | — |
| [hadynz/obsidian-kindle-plugin](https://github.com/hadynz/obsidian-kindle-plugin) (1.3k★) | "Obsidian Kindle Plugin" | none |

**Calibre** gives the feature no Kindle-branded name at all. Its [FAQ](https://manual.calibre-ebook.com/faq.html) calls it "Sharing books by email" under "Preferences → Sharing", with the toolbar buttons "Connect/share" and "Send to device". Kindle appears only in the instructions (for example "Amazon have announced that they will stop accepting MOBI files emailed to @kindle.com email addresses").

What these tools have in common:

- Almost every tool names Kindle, because it is the only honest way to say what the tool does.
- The bigger, longer-lived projects use a name that is not Amazon's product name: they coin a word (KindleEar, KindBeamer, KCC) or use a different verb (Push to Kindle).
- Exact "Send to Kindle" names do exist, but on small projects or in third-party stores. None of them is a published, curated package of the kind this plugin would be on plugins.omarchy.org.
- The one documented forced rename comes from a store's rules, not from Amazon: Apple made FiveFilters change "Push to Kindle" to "Push **for** Kindle". That matches Amazon's own "for/to" wording.

## 3. Takedowns or renames over the Kindle mark

- I found **no public case** of Amazon forcing an open-source Kindle tool to be removed or renamed on trademark grounds. Amazon's DMCA notices on GitHub that I found were about copyright (for example a [2021 notice about test questions](https://git.randommeaninglesscharacters.com/github/dmca/src/branch/master/2021/04/2021-04-27-amazon.md), and APKs in 2024), not the Kindle name. (This is an absence in search results, not proof that none exists.)
- On GitHub, trademark complaints go through the [trademark policy](https://docs.github.com/en/site-policy/content-removal-policies/github-trademark-policy), not the DMCA. That policy targets use "in a manner that may mislead or confuse others with regard to its brand or business affiliation". When the confusion looks unintentional, GitHub gives the account holder a chance to fix it before taking action. People reporting a complaint must certify they have "taken nominative and other fair uses into consideration".
- Store rules (Apple's, as above) are a more immediate pressure than Amazon itself. The Omarchy marketplace's own naming rules were not part of this ticket.

## 4. The plugin id `sorydi3.kindle-send`

- The id is a namespaced technical identifier, prefixed with the author's handle. It is not a product name shown to users, and it carries no "Send to Kindle" wording or logo. Amazon's developer rule covers app *titles*.
- Read literally, the Associates rule ("any application, plug-in or other software name") would cover `kindle-send` too. But the same rule would cover every project in the table above, and it binds only affiliates.
- `kindle-send` is also the name of the command (`bin/kindle-send`) and of an unrelated, popular Go tool. Users already know the name as a description, not as Amazon's.

## Recommendation

*(Recommendation, not legal advice.)*

1. **Rename the display name.** Today it is `"name": "Send to Kindle"` in `plugin/manifest.json`, and the same name appears in the menu entries, the Nautilus/Strata right-click item, the "Set up Send to Kindle" title, the spec and `PRODUCT.md`. Exactly copying Amazon's product name is the one choice that clashes with all of Amazon's published guidance and with how the established projects behave. Pick a name that keeps "Kindle" only as a "for"/"to" descriptor. Candidates, from the most cautious:
   - **"Kindle Send"**: matches the id and the command, and is not Amazon's product name. It still starts with the mark.
   - **"Book Sender for Kindle"** / **"Ebook Send for Kindle"**: the exact "X for Kindle" shape Amazon's developer guideline and Apple's rename both point to.
   - A coined name (like KindBeamer or KindleEar) if a distinctive brand is wanted.
2. **Add an "unofficial" statement**, not an "(Unofficial)" suffix on the name. Put it in the manifest `description` (for example "Unofficial. Send ebooks to your Kindle by email or USB. Not affiliated with or endorsed by Amazon.") and near the top of the README ("kindle-send is not created, affiliated with or endorsed by Amazon. Kindle is a trademark of Amazon.com, Inc. or its affiliates."). This follows rule 4 of Amazon's developer guideline and the KCC/KindBeamer practice.
3. **No Amazon logos or Kindle artwork** in the plugin icon, the screenshot or the marketplace listing (developer guideline rule 2).
4. **Keep the id `sorydi3.kindle-send`** and the `kindle-send` command. Both are descriptive and namespaced, and changing the id would also cost Settings, since disabling or removing a plugin deletes its `shell.json` entry (#46 notes). Only if the author wants to remove all risk would `sorydi3.ebook-send` or similar remove the mark from identifiers too. Nothing found suggests that is needed.
5. **Keep describing the feature with "Send to Kindle"**, for example "uses your Send to Kindle email address". That is an accurate reference to Amazon's service and is how Calibre, FiveFilters and others write their instructions.

## Open for the author

- Choose the new display name. The rename spreads through the manifest, the i18n catalog, the menu block, the Nautilus and Strata action labels, `PRODUCT.md`, `docs/spec.md` and `docs/manual-checks.md`.
- Check plugins.omarchy.org for its own naming or trademark rules before submitting (not covered here).
