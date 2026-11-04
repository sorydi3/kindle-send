# How does a Kindle behave over USB on Linux?

Type: research
Status: resolved
Blocked by: none
Parent: ../map.md

## Question

For the USB route on Arch-based Omarchy: does the user's kind of Kindle mount as USB mass storage or MTP (newer models switched to MTP), and which tools handle each? Which formats can be read when copied directly (EPUB is not native over USB on older firmware), which folder to copy into, how to reliably detect that a Kindle is plugged in, and how to safely unmount or eject it. Note which Kindle model the user has, if it can be found out without asking (otherwise list per-model differences).

## Answer

Full findings: branch `research/usb-route`, file `research/usb-route.md` (commit 6a25db5; never merged). No Kindle was plugged in, so the user's model is unknown.

- Two modes: older Kindles (Paperwhite 11th gen and earlier, Kindle 2022, Oasis) mount as a mass-storage drive labelled `Kindle`; Scribe (firmware 5.16.3+) and all 2024 Kindles use MTP.
- Installed already: `udisks2`, `gvfs-mtp`, `libmtp`, `nautilus`, `fuse3`; `udiskie --automount` runs at login, so a mass-storage Kindle mounts at `/run/media/sorydi3/Kindle`. Only one program can hold an MTP device at a time.
- Copy into the top-level `documents/` folder; on MTP find the storage path at runtime with `gio list`.
- Formats over USB: AZW3, AZW, KFX, MOBI, PRC, TXT, PDF. **EPUB is not readable over USB on any firmware**, so the USB route must convert EPUB (e.g. to AZW3 with Calibre's `ebook-convert`, not installed).
- Detection: vendor id `1949` (`lsusb -d 1949:`); MTP mode has udev `ID_MTP_DEVICE=1`; mass storage is a block device with `ID_VENDOR_ID=1949`.
- Eject: `udisksctl unmount` + `power-off` for mass storage; `gio mount -u mtp://...` or `fusermount3 -u` for MTP.
- Open: which Kindle the user has, and the real MTP storage path.
