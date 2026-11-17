// What the bar widget shows (spec §17). Pure functions, no QML.
// The text moves into the i18n catalog later (#65).
.pragma library

const NAME = "Books to Kindle"

// service: this plugin's Service ({ pending, held, busy }), or null before it loads.
// Returns { label, active, tooltip }: label is the count beside the icon, or ""
// when nothing waits; active while a Send runs.
function status(service) {
  const waiting = service && service.pending ? service.pending.length : 0
  const held = service && service.held ? service.held.length : 0
  const count = waiting + held
  const sending = !!service && service.busy === true
  const parts = []
  if (sending) parts.push("Sending…")
  if (waiting > 0) parts.push(waiting + " waiting for Kindle")
  if (held > 0) parts.push(held + " held by the Send limit")
  return {
    label: count > 0 ? String(count) : "",
    active: sending,
    tooltip: NAME + "\n" + (parts.length ? parts.join(" · ") : "Nothing waiting")
  }
}
