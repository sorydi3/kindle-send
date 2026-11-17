// Stands in for the Picker's PanelWindow in the preview (render.sh swaps it
// in): the offscreen platform has no Wayland compositor for a layer-shell
// window, so the scrim and card are drawn into the preview scene instead.
import QtQuick

Item {
  property color color: "transparent"
  anchors.fill: parent
}
