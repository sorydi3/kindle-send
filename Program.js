// Where the kindle-send bundled in the plugin folder is (spec §17). The Picker
// and the Service run it by this path, never from PATH, so a plain
// `omarchy plugin add` install works with nothing else installed.
.pragma library

// url: Qt.resolvedUrl("bin/kindle-send") from a QML file at the plugin root.
function path(url) {
  return decodeURIComponent(String(url).replace(/^file:\/\//, ""))
}
