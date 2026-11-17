// Stands in for Omarchy's qs.Commons Translations in English: reads
// <directory>/en.json (file reads need QML_XHR_ALLOW_FILE_READ=1).
import QtQuick

QtObject {
  id: root
  property var directory: ""
  readonly property var strings: {
    const xhr = new XMLHttpRequest()
    xhr.open("GET", String(root.directory).replace(/\/+$/, "") + "/en.json", false)
    xhr.send()
    try { return JSON.parse(xhr.responseText) } catch (e) { return ({}) }
  }

  function t(key, fallback) {
    let v = root.strings[key]
    if (v && typeof v === "object") v = v.other
    return typeof v === "string" && v.length > 0 ? v : (fallback !== undefined ? fallback : key)
  }

  function tn(key, count, fallback) {
    let v = root.strings[key]
    if (v && typeof v === "object") v = count === 1 && v.one ? v.one : v.other
    return typeof v === "string" && v.length > 0 ? v : (fallback !== undefined ? fallback : key)
  }
}
