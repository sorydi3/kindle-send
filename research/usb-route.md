# USB route: how a Kindle behaves over USB on Omarchy (Arch)

Answers ticket `.scratch/kindle-send/issues/02-usb-route-facts.md`. Researched 2026-11-04.

Notes on sources: Amazon's help pages on `amazon.com/gp/help/...` returned HTTP 503 to the fetcher. The same pages are served from Amazon's own mirror at `digprjsurvey.amazon.com/csad/help/node/<nodeId>`, which is what's cited here. Claims tagged **[local]** were checked on this machine with `pacman`, `command -v`, `lsusb`, the udev hwdb files and man pages.

## TL;DR

- Two USB behaviours exist. **Older Kindles show up as USB mass storage**: a FAT drive labelled `Kindle` with a `documents/` folder. **Kindle Scribe (after firmware 5.16.3, 2023) and all 2024 and newer Kindles use MTP**, which gives no block device and no drive letter.
- The user's model is **unknown**, because no Kindle was plugged in when `lsusb` ran. The tool has to handle both modes.
- Mass storage on this machine: **udiskie is already running with `--automount`** (started by Omarchy's Hyprland autostart), so a Kindle drive mounts itself under `/run/media/$USER/Kindle`. Eject it with `udisksctl unmount` and then `udisksctl power-off`.
- MTP on this machine: `gvfs-mtp`, `libmtp` (its `mtp-*` CLI tools) and `nautilus` are installed. `jmtpfs`, `simple-mtpfs` and `go-mtpfs` are **not** installed; they are AUR-only. `mtpfs` and `android-file-transfer` are in `extra` but not installed. Only one process can hold an MTP device at a time.
- Copy books into `documents/`. Formats the device reads natively when sideloaded: **AZW3, AZW, AZW1, KFX, MOBI, PRC, TXT, PDF**. **EPUB is not in any Amazon list of sideload-readable formats.** Amazon accepts it only through Send to Kindle, which converts it server-side. So the USB route needs EPUB→AZW3 conversion, for example with calibre's `ebook-convert`, which is not installed.
- Detection: USB vendor id **`1949`** (Lab126 = Amazon). Tell the two modes apart by udev property `ID_MTP_DEVICE=1` (MTP) or by a block device with `ID_VENDOR_ID=1949` (mass storage).

## 1. Mass storage vs MTP, per model and firmware

| Model | USB mode | Source |
|---|---|---|
| Kindle Scribe (2022), firmware < 5.16.3 | Mass storage | [the-ebook-reader, 2023-09-01][teb-mtp] |
| Kindle Scribe (2022), firmware ≥ 5.16.3 (July/Aug 2023) | **MTP** | [teb-mtp]; MobileRead release-notes thread ["Connect Kindle Scribe over USB using Media Transfer Protocol (MTP) instead of emulating a disk drive"][mr-5163]. Amazon's own notes only said "performance improvements". |
| 2024-released Kindles: Kindle (11th gen, 2024), Paperwhite (12th gen), Colorsoft, Scribe 2024 | **MTP** | Amazon: "Kindle Scribe and 2024-released Kindle devices require a separate application" for USB on Mac ([Amazon help TCUBEdEkbIhK07ysFu][amz-usb]). The extra app is needed because macOS has no native MTP. calibre 7.25: "Allow import of KFX files from 2024 Kindles that use the MTP protocol"; calibre 8.7: "2024 and newer MTP based Kindles" ([calibre what's new][cal-new]) |
| Later Scribe models (Scribe Colorsoft, Scribe 3rd gen, Scribe without front light) | Presumably MTP, since they are newer than 2024. **Not confirmed by a primary source.** | [Amazon firmware page][amz-fw] lists them on firmware 5.20.1 |
| Paperwhite 11th gen (2021), Kindle 11th gen 2022, Oasis 10th gen and older | Mass storage. No source says these switched; they stay on firmware 5.19.2 / 5.18.x | [amz-fw]; [Kindle Paperwhite User's Guide][kug]: "it will appear as an external storage drive or volume… contains a folder called 'documents.'" |

Amazon's own USB page does not use the word "MTP". It only says a separate app is needed on Mac ([amz-usb]). The MTP fact comes from calibre's changelog and from libmtp, which lists `Kindle Scribe 32GB` as `0x1949:0x9981` with `DEVICE_FLAGS_ANDROID_BUGS` ([libmtp music-players.h][libmtp-src]; same entry in local `/usr/lib/udev/hwdb.d/69-libmtp.hwdb` **[local]**). 2024 Kindles other than the Scribe have **no** explicit libmtp entry. They are still flagged as MTP, because udev rule `/usr/lib/udev/rules.d/69-libmtp.rules` runs `mtp-probe` on unknown devices and sets `ID_MTP_DEVICE=1` when the probe succeeds **[local]**.

## 2. Tools on this machine **[local]**

| Tool | Package | Installed? | Handles |
|---|---|---|---|
| `udisksctl` | `udisks2` 2.11.2 | yes | Mass storage: `mount`, `unmount`, `power-off` (man udisksctl) |
| `udiskie --automount` | `udiskie` 2.7.0 | yes, **running** (from `/usr/share/omarchy/default/hypr/autostart.lua`) | Automounts mass-storage Kindles under `/run/media/sorydi3/<LABEL>` |
| `gio mount` / gvfsd-mtp | `gvfs` + `gvfs-mtp` 1.62 | yes | MTP via `mtp://…` URIs. FUSE view at `/run/user/1000/gvfs/mtp:host=…` (`gvfs-mtp-volume-monitor` user service, currently inactive). `mtp.mount` has `AutoMount=false`, so nothing grabs the device until Nautilus or `gio` asks for it. |
| `nautilus` | `nautilus` 51.1 | yes | GUI for both, using gvfs |
| `mtp-detect`, `mtp-files`, `mtp-folders`, `mtp-sendfile`, `mtp-newfolder`, `mtp-delfile` | `libmtp` 1.1.23 | yes | Scriptable MTP access with no FUSE needed |
| `jmtpfs` | AUR `jmtpfs` 0.5 ([github.com/JasonFerrara/jmtpfs][jmtpfs]) | **no** | FUSE mount of MTP |
| `simple-mtpfs` | AUR `simple-mtpfs` 0.4.0 ([github.com/phatina/simple-mtpfs][smtpfs]) | **no** | FUSE mount of MTP |
| `go-mtpfs` | AUR `go-mtpfs-git` ([github.com/hanwen/go-mtpfs][gomtpfs]) | **no** | FUSE mount of MTP |
| `mtpfs` | extra `mtpfs` 1.1 | no | FUSE mount of MTP |
| `android-file-transfer` (`aft-mtp-mount`) | extra 4.6 | no | MTP GUI and FUSE |
| `calibre` / `ebook-convert` | extra `calibre` 9.14 | **no** | Conversion, plus Kindle drivers for both modes |
| `fusermount3` | `fuse3` 3.18 | yes | Unmounting FUSE MTP mounts |

`yay` is present, so AUR packages could be installed, but per the ticket nothing was installed.

**One owner at a time (MTP):** on Linux only one program can hold an MTP session. If Nautilus or gvfs has opened the Kindle, calibre, `mtp-*` and jmtpfs fail to connect. The usual workaround is to unmount the gvfs MTP mount first (`gio mount -u mtp://…`) or stop `gvfs-mtp-volume-monitor`. This comes from user reports, for example [r/linuxmint thread][reddit-mint] and [r/Calibre 2024 Paperwhite thread][reddit-cal]; it is not an official doc.

## 3. Formats readable when copied directly

- Amazon's Kindle user guide lists sideloadable/downloadable types as "Kindle content (.AZW, .AZW1, .AZW3, and .KFX), unprotected Mobipocket books (.MOBI, .PRC), and text files (.TXT)" and says "You can also read documents in PDF and TXT format natively" ([kug], ch. 7).
- **EPUB:** Amazon's Send to Kindle page lists EPUB as accepted ([Amazon help G5WYD9SAF7PGXRNA][amz-fmt]), but delivery that way goes through Amazon's conversion service. No Amazon page lists EPUB as readable when copied over USB on any firmware, and calibre's Kindle MTP driver `format_map` leaves it out: `['azw3', 'mobi', 'azw', 'azw1', 'azw4', 'pdf']` ([calibre mtp/driver.py][cal-mtp]). Treat EPUB as **not readable over USB on every model and firmware**, and convert it to AZW3 first. calibre 8.6 changed its default Kindle output to AZW3 "as MOBI is obsolete" ([cal-new]).
- Colorsoft: sideloaded PDFs display without colour, and sideloaded books often show no cover in the library. These are user reports ([the-ebook-reader 2024-11-11][teb-color]). calibre works around the cover problem by writing `system/thumbnails` ([cal-mtp]).

## 4. Where to copy

- Into the top-level **`documents/`** folder ([kug]: "This Kindle volume contains a folder called 'documents.'"; Amazon Mac USB page: drag files to the "Documents" folder ([amz-usb])). Subfolders are allowed.
- Limits on Amazon's USB page: no more than 2,000 files per transfer, and on Windows the full file path must stay under 256 characters ([amz-usb]). calibre limits Kindle MTP paths to 245 characters (225 for KFX) ([cal-mtp]).
- With MTP the top level is an MTP *storage* object, not a filesystem root. Under gvfs the path looks like `mtp://<device>/<storage name>/documents/`. The exact storage name (for example "Internal Storage") was **not verified**; enumerate it at runtime with `gio list mtp://…/` or `mtp-folders`.

## 5. Detecting a plugged-in Kindle

- Vendor id **`1949`** is assigned to "Lab126, Inc." (Amazon's device subsidiary) in the systemd hwdb, which comes from usb.ids (`/usr/lib/udev/hwdb.d/20-usb-vendor-model.hwdb` **[local]**). Mass-storage e-readers commonly enumerate as `1949:0004` ("Amazon Kindle 3/4/Paperwhite"). The MTP Scribe is `1949:9981` ([libmtp-src]). Product ids for 2024 MTP Kindles were not found in a primary source, so **match on vendor only**. Be aware that vendor 1949 also covers Fire tablets, the Fire Phone and an Amazon security key (`1949:0417`) **[local]**.
- Simple check: `lsusb -d 1949:`.
- Mode check:
  - Mass storage: `lsblk -o NAME,LABEL,MOUNTPOINT` or `udevadm info` on the block device shows `ID_VENDOR_ID=1949`. The filesystem label is normally `Kindle`, and udiskie mounts it at `/run/media/$USER/Kindle` **[local]**.
  - MTP: the USB device has `ID_MTP_DEVICE=1` (`udevadm info /dev/bus/usb/BBB/DDD`), and `gio mount -l` lists an `mtp://` volume. `mtp-detect` also works but takes the MTP session.
- Event-driven option: `udevadm monitor --udev --subsystem-match=usb` or `gio mount -o` (monitor).
- At research time `lsusb` showed **no 1949 device**, so the user's model could not be identified **[local]**.

## 6. Ejecting safely

- Mass storage: `udisksctl unmount -b /dev/sdX1`, then `udisksctl power-off -b /dev/sdX`. power-off "ensur[es] that no process is using the drive, then request[s] that in-flight buffers and caches are committed to stable storage… the USB device will be deconfigured" (man udisksctl **[local]**). Amazon's guide says to unmount/eject "so that your Kindle exits USB drive mode" ([kug]).
- MTP: writes go straight to the device and there is nothing to sync. Release the session so the Kindle leaves USB mode: `gio mount -u mtp://…` for gvfs, or `fusermount3 -u <mnt>` for jmtpfs/simple-mtpfs/go-mtpfs. Amazon: "select the Disconnect button on the Kindle screen or unplug the USB cable" ([amz-usb]).

## Open questions

- Which Kindle the user actually has. Run `lsusb -d 1949:` with it plugged in, or ask.
- The MTP storage name and `documents` path on 2024 Kindles; check with `gio list` when a device is available.
- Whether the post-2024 Scribe models (Colorsoft, 3rd gen) are MTP. This is very likely but unconfirmed.

[amz-usb]: https://digprjsurvey.amazon.com/csad/help/node/TCUBEdEkbIhK07ysFu "Amazon: Connect, Browse, and Transfer Files on E-Reader"
[amz-fmt]: https://digprjsurvey.amazon.com/csad/help/node/G5WYD9SAF7PGXRNA "Amazon: Send to Kindle supported file types"
[amz-fw]: https://digprjsurvey.amazon.com/csad/help/node/GKMQC26VQQMM8XSW "Amazon: Kindle E-Reader Software Updates"
[kug]: https://d1ergij2b6wmg5.cloudfront.net/EM10/Kindle_User_Guide_en-US.pdf "Kindle Paperwhite User's Guide, 2nd Edition (Amazon CDN)"
[cal-new]: https://calibre-ebook.com/whats-new "calibre changelog"
[cal-mtp]: https://github.com/kovidgoyal/calibre/blob/master/src/calibre/devices/mtp/driver.py "calibre MTP driver"
[libmtp-src]: https://github.com/libmtp/libmtp/blob/master/src/music-players.h "libmtp device list"
[jmtpfs]: https://github.com/JasonFerrara/jmtpfs
[smtpfs]: https://github.com/phatina/simple-mtpfs/
[gomtpfs]: https://github.com/hanwen/go-mtpfs
[teb-mtp]: https://blog.the-ebook-reader.com/2023/09/01/kindle-scribe-now-supports-mtp-instead-of-usb-mass-storage-after-update/
[teb-color]: https://blog.the-ebook-reader.com/2024/11/11/kindle-colorsoft-doesnt-support-color-on-sideloaded-pdfs/
[mr-5163]: https://www.mobileread.com/forums/showthread.php?p=4352484
[reddit-mint]: https://www.reddit.com/r/linuxmint/comments/1kussoq/linux_mint_no_longer_recognizes_my_kindle/
[reddit-cal]: https://www.reddit.com/r/Calibre/comments/1gpc0s9/kindle_paperwhite_signature_edition_2024_not/
