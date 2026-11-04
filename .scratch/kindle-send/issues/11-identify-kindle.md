# Which Kindle does the user have, and how does it show up over USB?

Type: task
Status: open
Blocked by: none
Parent: ../map.md

## Question

HITL: the user plugs the Kindle into this machine; the agent then runs, AFK:

1. `lsusb -d 1949:` to get the product id and model.
2. `udevadm info` on the device to see whether it is MTP (`ID_MTP_DEVICE=1`) or mass storage.
3. If mass storage: confirm it auto-mounts at `/run/media/sorydi3/Kindle` and has `documents/`.
4. If MTP: `gio mount -li` and `gio list mtp://...` to find the real path to `documents/`.

Record the model, the mode and the exact path. See [How does a Kindle behave over USB on Linux?](02-usb-route-facts.md).
