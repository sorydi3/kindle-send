# How is the Route chosen for each Send?

Type: grilling
Status: resolved
Blocked by: 01, 02
Parent: ../map.md

## Question

When does a Send go by email and when by USB? Options include: always ask, automatic by file size and format, prefer USB whenever a Kindle is plugged in, or a default with an override. What happens when the chosen Route can't work (file too big for email, no Kindle plugged in)?

## Answer

Decided with the user (grilling, 2026-11-04):

1. **Automatic per Book, with override.** Email if Amazon accepts the format by email and the Book is within the Email limit (Gmail's, read from the server at send time); otherwise USB (too big, or a USB-only format such as AZW3, MOBI, KFX). The picker shows each Book's Route and lets the user switch it before sending.
2. **Email wins when both work**, even with the Kindle plugged in (cloud library, sync, Amazon converts EPUB).
3. **USB with no Kindle plugged in → Pending Send.** Held in memory and sent automatically when the Kindle is next plugged in; notify when it is queued and when it goes. Forgotten if the shell restarts (no saved queue).
4. **Route is per Book**, so one Send can use both Routes.
5. **One email per Book.**
6. **No automatic fallback** from a failed email to USB: notify with the reason, and the user resends.
