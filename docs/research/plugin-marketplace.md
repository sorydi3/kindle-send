# Research: the Omarchy plugins marketplace and what a listing needs

Ticket: #48 (map #46). Researched 2026-11-13. Nothing was submitted.

## Answer

- **There is one marketplace, under two domains.** `omarchyplugins.com` (and `www.`) answers `301 Moved Permanently` → `https://plugins.omarchy.org/` (checked with `curl -I`, 2026-11-13). The Omarchy manual names plugins.omarchy.org. The marketplace's own README still links to `omarchyplugins.com`. The site's source is `omacom/omarchy-plugin-marketplace` (MIT, created 2026-07-28, last push 2026-11-13). The footer credits HANCORE as the builder.
- **You submit by opening a GitHub issue** on `omacom/omarchy-plugin-marketplace`, with the "Submit a plugin" form or `gh issue create` in a fixed format. A bot validates the repo and runs a static security scan. A maintainer then publishes it with the `approved-and-verified` label.
- **What a listing needs:** a public GitHub repo with `manifest.json` at the root, a root README with install **and removal** instructions, a root LICENSE file, a globally unique lowercase id outside `omarchy.*`, one category and 1–3 tags chosen from fixed lists, and the manifest fields `author` and `description`. A root `preview.png` is optional. A minimum Omarchy version isn't asked for, and the validator has no such field.
- **Gaps in kindle-send today:** the manifest has no `author` (the marketplace requires it) and no `license`. The repo has no root README, LICENSE or preview. The name "Send to Kindle" is already taken by a listed plugin with nearly the same features (see below).

## 1. Which marketplace is current

The Omarchy manual (<https://omarchy.org/manual/shell-plugins/>, undated, fetched 2026-11-13):

> "To help people actually find it, list it at plugins.omarchy.org." … "That's the marketplace for Omarchy shell plugins." … "put it in a public git repo. That's the whole distribution mechanism." … "anyone can then run `omarchy plugin add` against your URL."

The manual says nothing about what a listing needs, how review works, or a minimum version.

`https://omarchyplugins.com` → `HTTP/2 301`, `location: https://plugins.omarchy.org/` (same for `www.`). So the two names the ticket asks about are the same site. The only disagreement is cosmetic: the marketplace README's banner and links still point at `omarchyplugins.com/…`.

plugins.omarchy.org calls itself a community registry "for Omarchy Quattro" and links to the GitHub repo for "Contribute a plugin". Fetched without JavaScript, the catalog showed "No plugins found" because the site renders client-side. The registry file shows it is far from empty. `registry.json` in the repo (2026-11-13) holds **6,527 sources**: 16 added in July 2026, 1,944 in August, 2,476 in September, 1,697 in October and 394 in November up to the 13th. Listings are still being added several times an hour (the last three commits on 2026-11-13 are "Add … plugin" merges).

## 2. How a plugin is submitted

The primary sources are `README.md`, `SUBMISSION.md`, `VERIFICATION.md` and `SECURITY.md` in `omacom/omarchy-plugin-marketplace` on `main` (2026-11-13), plus `.github/ISSUE_TEMPLATE/submit-plugin.yml`.

1. You keep the code in your own repo. The form says: "Keep the plugin code, releases, and documentation in your own public GitHub repository."
2. You open an issue titled `[Plugin]: <name>` with the [submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml) or with `gh issue create --repo omacom/omarchy-plugin-marketplace --title "[Plugin]: …" --body-file …`. The body has six headings in a fixed order: Repository URL, Category, Tags, Suggest a missing tag, Maintainer notes, Submission checklist. All five checklist boxes must be ticked:
   - "The repository is public and contains installation and removal instructions."
   - "I have documented the plugin license and any external dependencies."
   - "I confirm that I own or have permission to submit this plugin and its preview assets."
   - "The plugin does not overwrite user configuration without explicit consent."
   - "I understand that approval is for listing and is not a security review."
3. A bot validates the structure and "Quattro compatibility" at an exact commit. Then the **Automated Security Baseline** runs. It is a static scan that reports `passed`, `review-required` or `needs-fixes`.
4. A maintainer publishes the listing: "A maintainer must still review the exact checked commit and apply `approved-and-verified` before it appears in the marketplace." (SUBMISSION.md)
5. Failed checks are fixed by editing the same issue, not by opening a new one: "Correct the existing repository or issue instead of opening a duplicate submission, then edit the issue to run validation again."
6. Updates aren't automatic for verification. SUBMISSION.md: "Use the single **Plugin verification** issue form, select **Verify and publish a newer upstream commit**…" Until you do, the listing shows `Update unverified` once upstream HEAD moves. Installs aren't pinned anyway. VERIFICATION.md: "The current Omarchy command clones the repository's mutable current HEAD and does not accept an exact marketplace commit."

SUBMISSION.md also has agent rules: an agent must "Ask the plugin owner to confirm the ownership statement and every other checklist item", must "Show the completed title and body to the owner", and must "Create the GitHub issue only after the owner explicitly approves". This matches #46's rule that submitting stays a manual step for the author.

## 3. What a listing needs

From SUBMISSION.md ("Check the repository"), enforced in `scripts/build-catalog.mjs` (`validateManifest`, `validateRepositoryDocs`):

| Requirement | Source | kindle-send today |
|---|---|---|
| Public repo, GitHub **root** URL | SUBMISSION.md | Private; manifest lives in `plugin/` and the root fails `validate` (#46) |
| One plugin, `manifest.json` at repo root | SUBMISSION.md | No (in `plugin/`) |
| `schemaVersion: 1`; `id`, `name`, `version`, **`author`**, `description` all non-empty strings | `validateManifest`: `const required = ["id", "name", "version", "author", "description"]` | **`author` missing** |
| `license` optional; if present, a non-empty string ≤120 chars. The catalog shows "See repository" when it's absent | `validateManifest`; `license: manifest.license \|\| "See repository"` | Missing (MIT is decided) |
| Field limits: id 128, name 120, version 64, author 120, description 500 | `manifestFieldLimits` | OK |
| Lowercase id matching `^[a-z0-9][a-z0-9._-]*$`, not `omarchy.*`, never used before (retired ids stay blocked). SUBMISSION.md suggests "a namespaced lowercase ID such as `io.github.yourname.plugin-name`" | SUBMISSION.md, `validateManifest` | `sorydi3.kindle-send` is valid and not taken |
| `kinds` drawn from `bar, bar-widget, menu, overlay, panel, service`, each with an entry point at a safe relative path that exists | `supportedKinds`, `validateManifestFiles` | OK (`menu`, `service`) |
| No symlinks in the plugin folder | `validateManifestFiles` | Fine for a repo-root layout. Today's `install.sh` symlinks are outside it |
| Root `README*` | `validateRepositoryDocs` (error `readme-missing`) | **Missing** |
| README covers installation **and removal** | Checklist item 1 (a human check, not a file check) | — |
| Root `LICENSE*` / `LICENCE*` / `COPYING*` | `validateRepositoryDocs` (error `license-missing`) | **Missing** |
| External dependencies documented | Checklist item 2 | — |
| Category: exactly one of `Appearance, Desktop, Developer Tools, Hardware, Kids, Productivity, System, Widgets, Other` | SUBMISSION.md | `Productivity` fits. Both Kindle plugins below use it |
| Tags: 1–3 of `ai, bar, education, games, hyprland, kids, launcher, media, power-management, quickshell, security, system, vpn, workspaces`, plus one optional suggested tag | SUBMISSION.md | No good fit. `quickshell` and `launcher` are the closest; maybe suggest `ebooks` |
| Preview (optional): root `preview.png/.jpg/.jpeg/.webp/.avif`, ≤50 MB, ≤40 MP. The marketplace resizes it, and uses a fallback image when there is none | SUBMISSION.md, `defaultPreviewPattern` | **Missing** |
| Minimum Omarchy version | Not asked for anywhere: not in the manual, the form or the validator. "Quattro compatibility" just means the manifest checks above | n/a |

**Review is not a security review.** SUBMISSION.md: "Marketplace validation checks repository structure and Omarchy Quattro compatibility. It is not a security review". The README says: "These checks are not a security audit, certification, endorsement, or guarantee".

**Likely scan outcome for kindle-send: `review-required`, not `needs-fixes`.** SECURITY.md lists `installer`, `package-manager` and `privilege` ("non-negated references to `sudo` or `pkexec`") as "review capabilities" that "require maintainer review but are not findings by themselves". The scanner (`scripts/security-baseline-analysis.mjs`) flags `pacman -S` as `package-manager` and any non-negated `sudo` as `privilege`. kindle-send prints `sudo pacman -S calibre` in `bin/kindle-send` and `scripts/install.sh`, and `install.sh` is a setup-named file. So expect those capabilities. A maintainer can accept them; only "selectively blocking findings" (download-to-shell, unpinned external git execution, dangerous passwordless sudoers rules, privileged process control from `/tmp` PID files) must be fixed first. I didn't run the scanner, so this is an inference from its source. In the registry, 3,064 of 6,527 sources are `review-required` and 3,359 are `passed`.

**The "Manual setup" status.** A maintainer can add the `manual-setup` label ("Standard install cannot produce a functioning plugin"). The listing then shows "Manual setup" and drops the copyable `omarchy plugin add … --enable` command (`build-catalog.mjs`, `installation.mode: "manual"`). If kindle-send needs `kindle-send` on `PATH` before the Picker works, it could get that status. The #46 bar ("`plugin add` plus at most one documented step") should be checked against this.

## 4. Listed plugins close to this one

From `registry.json` (2026-11-13), two listed plugins involve Kindle:

- **`io.github.simplici0.send-to-kindle`** — <https://github.com/Simplici0/omarchy-send-to-kindle>, listed 2026-10-04, baseline `passed`, Productivity with tags `bar` and `quickshell`, MIT, 1 star. Its manifest `name` is **"Send to Kindle", the same name as ours**. It's a bar widget that sends EPUB/PDF by SMTP. The password lives in gnome-keyring through `secret-tool`, and it uses `python3`, stdlib only. That is close to kindle-send's email path. It has no USB mode, no Nautilus integration and no conversion.
- **`minholi.kindle`** ("OmaKindle") — <https://github.com/minholi/omakindle>, listed 2026-09-21, `passed`. It is a read-only library and highlights viewer, not a sender.

A search of the registry for `kindle`, `ebook`, `epub` and `calibre` found nothing else.

## 5. What listed plugins commonly do that kindle-send lacks

Taken from the two Kindle plugins above and from the shell reference's sample manifest (`omacom/omarchy` `docs/omarchy-shell.md`, branch `quattro`, last changed 2026-10-24), which includes `"author": "You"`:

- `author` and `license: "MIT"` in `manifest.json`.
- A root `preview.png`, shown at the top of the README.
- README sections: **Install** (`omarchy plugin add https://github.com/<you>/<repo> --enable`), **Update** (`omarchy plugin update <id>`), **Requires** (listing what Omarchy already ships), **Use**, **Configure**, **Remove/Uninstall** (`omarchy plugin disable/remove <id>` plus removing stored secrets and data, e.g. `secret-tool clear …`), and **Security** ("Unsandboxed by design…"; what leaves the machine).
- OmaKindle also declares settings in the manifest (`barWidget.defaults` and `schema`) plus `aliases` for search. Those belong to bar widgets; kindle-send is a `menu` and `service` plugin and has its own Settings in the Picker.

## Unknowns and caveats

- The manual page shows no date. The marketplace docs change daily, so the rules above are as of 2026-11-13.
- I read the marketplace's catalog through `registry.json` and the scripts, not through the rendered site, because the site needs JavaScript.
- I didn't run the security scan on kindle-send. The `review-required` estimate comes from reading the scanner's patterns.
- I couldn't confirm who decides on `manual-setup` or when, beyond the label's description and the code path.
