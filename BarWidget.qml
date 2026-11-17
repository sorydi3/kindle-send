// The bar widget (spec §17): a book icon that toggles the Picker on left-click,
// the count of Books waiting for the Kindle plus emails held by the Send limit
// beside it, and the bar's active colour while a Send runs. No right-click action.
// What it shows comes from Bar.js; this file only renders it.
import QtQuick
import qs.Ui
import "Bar.js" as Bar

BarWidget {
  id: root
  moduleName: "sorydi3.kindle-send"

  // This plugin's own Service. Bar.status reads its pending, held and busy,
  // so the binding follows them.
  readonly property var service: bar && bar.shell ? bar.shell.serviceFor("sorydi3.kindle-send") : null
  // The plugin's own text (i18n/), in the language picked under Setup > Language.
  Translator {
    id: tr
  }
  readonly property var status: Bar.status(service, tr)

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\u{F02D}"
    labelText: root.status.label
    active: root.status.active
    tooltipText: root.status.tooltip
    onPressed: function (pressed) {
      if (!root.bar || pressed === Qt.RightButton)
        return;
      root.bar.run("omarchy-shell shell toggle sorydi3.kindle-send");
    }
  }
}
