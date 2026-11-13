// PROTOTYPE, throwaway: "Bar widget: what it shows and does" (#56), branch
// prototype/bar-widget, never merged. Right-click cycles three variants;
// left-click opens the Picker. The tooltip names the variant and the state.
import QtQuick
import qs.Ui

BarWidget {
  id: root
  moduleName: "sorydi3.kindle-send"

  property int variant: 0
  readonly property var names: ["A: icon only", "B: icon + count", "C: quiet until busy"]

  // This plugin's own Service: Books waiting for the Kindle, emails held by the Send limit, a Send running.
  readonly property var service: bar && bar.shell ? bar.shell.serviceFor("sorydi3.kindle-send") : null
  readonly property int waiting: service && service.pending ? service.pending.length : 0
  readonly property int held: service && service.held ? service.held.length : 0
  readonly property bool sending: service ? service.busy === true : false
  readonly property int count: waiting + held
  readonly property bool idle: count === 0 && !sending

  function stateText() {
    const parts = []
    if (sending) parts.push("Sending…")
    if (waiting > 0) parts.push(waiting + " waiting for Kindle")
    if (held > 0) parts.push(held + " held by the Send limit")
    return parts.length ? parts.join(" · ") : "Nothing waiting"
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\u{F02D}"
    labelText: root.variant > 0 && root.count > 0 ? String(root.count) : ""
    active: root.variant > 0 && root.sending
    dimmed: root.variant === 2 && root.idle
    tooltipText: "Books to Kindle\n" + root.stateText() + "\n[prototype " + root.names[root.variant] + "; right-click: next]"
    onPressed: function(b) {
      if (!root.bar) return
      if (b === Qt.RightButton) root.variant = (root.variant + 1) % 3
      else root.bar.run("omarchy-shell shell toggle sorydi3.kindle-send")
    }
  }
}
