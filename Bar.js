// What the bar widget shows (spec §17). Pure functions, no QML.
// tr: the translator (Catalog.js).
.pragma library
.import "Catalog.js" as Catalog

const LEFT_BUTTON = 0x1  // Qt.LeftButton

// Whether a press of `button` (WidgetButton's pressed(button)) toggles the
// Picker: a left-click only; middle and right clicks do nothing.
function togglesPicker(button) { return button === LEFT_BUTTON }

// service: this plugin's Service ({ pending, held, busy }), or null before it loads.
// Returns { label, active, tooltip }: label is the count beside the icon, or ""
// when nothing waits; active while a Send runs.
function status(service, tr) {
  const waiting = service && service.pending ? service.pending.length : 0
  const held = service && service.held ? service.held.length : 0
  const count = waiting + held
  const sending = !!service && service.busy === true
  const parts = []
  if (sending) parts.push(tr.t("bar.sending"))
  if (waiting > 0) parts.push(Catalog.count(tr, "bar.waiting", waiting))
  if (held > 0) parts.push(Catalog.count(tr, "bar.held", held))
  return {
    label: count > 0 ? tr.num(count) : "",
    active: sending,
    tooltip: tr.t("app.name") + "\n" + (parts.length ? parts.join(tr.t("list.dot")) : tr.t("bar.idle"))
  }
}
