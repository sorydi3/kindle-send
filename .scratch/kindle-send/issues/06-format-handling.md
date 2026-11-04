# Do Books get converted before sending, and with what?

Type: grilling
Status: open
Blocked by: 01, 02
Parent: ../map.md

## Question

Given which formats each Route accepts: does the plugin convert anything (e.g. EPUB to AZW3 for USB, via Calibre's `ebook-convert`, which is not installed today), refuse unsupported files, or only send what each Route accepts as-is?

## Context from Route choice

Per [How is the Route chosen for each Send?](05-route-choice.md), email wins whenever it can, so EPUBs normally go by email and Amazon converts them. Conversion only matters for an EPUB that goes over USB: one above the Email limit, or one the user switched to USB.
