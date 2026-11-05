import QtQuick

QtObject {
  property string text: ""
  function reset() { text = "" }
  function feed(line) { text += line + "\n" }
}
