// The preview scene (docs/preview/render.sh runs it offscreen): the plugin's
// own Picker over the theme's wallpaper, with one Book marked, and Omarchy's
// own notification card showing what the Service posts when a Book is sent.
import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import "plugin" as P
import "plugin/Feedback.js" as Feedback
import "notifications" as N

ShellRoot {
  id: shell

  readonly property string out: Quickshell.env("PREVIEW_OUT")
  readonly property string wallpaper: Quickshell.env("PREVIEW_WALLPAPER")

  // Only what the Picker reads from its Service; nothing here sends.
  QtObject {
    id: fakeService
    property var pending: []
    property var held: []
    property bool busy: false
    property var testSend: null
    function enqueue(books) {}
    function cancelPending() {}
    function sendTest(sender) {}
  }

  P.Translator { id: tr }

  // The summary the Service posts for one Book sent by Email.
  readonly property var sent: Feedback.summary([{ name: "Pride and Prejudice.epub", result: "sent" }], null, tr)

  FloatingWindow {
    id: scene
    implicitWidth: 1200
    implicitHeight: 750
    color: Commons.Color.background
    visible: true

    // What is grabbed: a window's own content item has no QML engine to grab with.
    Item {
      id: stage
      anchors.fill: parent

      Image {
        anchors.fill: parent
        visible: shell.wallpaper !== ""
        source: shell.wallpaper ? "file://" + shell.wallpaper : ""
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: 2400
      }

      // The Picker, scrim and card, drawn into the scene (PreviewPanel.qml).
      P.Picker {
        id: picker
        anchors.fill: parent
        service: fakeService
      }

      N.Toast {
        id: toast
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: Style.gapsOut * 2
        anchors.rightMargin: Style.gapsOut * 2
        cardWidth: Style.space(380)
        sole: true
        row: ({
          key: "preview", app: tr.t("app.name"), glyph: "\u{F02D}", urgency: 1,
          summary: shell.sent.headline, body: shell.sent.body, bodyRich: shell.sent.body,
          ts: Date.now() / 1000, duration: 0
        })
      }
    }
  }

  property int step: 0
  Timer {
    interval: 250
    repeat: true
    running: true
    onTriggered: {
      if (shell.step === 0) {
        if (picker.loading || picker.books.length === 0) return
        // One Book marked, the cursor on the newest.
        var marked = {}
        for (var i = 0; i < picker.books.length; i++)
          if (picker.books[i].name === "Moby Dick.pdf") marked[picker.books[i].path] = true
        picker.marked = marked
        picker.selectedIndex = 0
        shell.step = 1
      } else if (shell.step < 4) {
        shell.step += 1  // a few frames for the marks and the wallpaper to settle
      } else if (shell.step === 4) {
        shell.step = 5
        stage.grabToImage(function(result) {
          if (result.saveToFile(shell.out)) console.log("PREVIEW SAVED", shell.out)
          else console.log("PREVIEW ERROR could not save", shell.out)
          Qt.quit()
        }, Qt.size(stage.width * 2, stage.height * 2))
      }
    }
  }

  Component.onCompleted: picker.open("")
}
