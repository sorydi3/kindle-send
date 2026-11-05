import QtQuick

QtObject {
  signal read(string data)
  function feed(line) { read(line) }
}
