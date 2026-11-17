// The demo scene (docs/preview/render-gif.sh runs it offscreen): the plugin's
// own bar widget and Picker over the theme's wallpaper, played through a
// timeline and grabbed frame by frame. The Picker is driven through its own
// functions, the ones its keys call (filterText, toggleMark, select,
// switchRoute, send, openSettings, leaveSettings, close); a key caption at the
// bottom names each key as it is used. The Service is a stand-in that sends
// nothing: what Enter hands it becomes Omarchy's own notification card, with
// the summary the plugin's Feedback.js writes for it.
import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "plugin" as P
import "plugin/Feedback.js" as Feedback
import "plugin/Routes.js" as Routes
import "notifications" as N
import "notifications/Markup.js" as Markup

ShellRoot {
  id: shell

  readonly property string out: Quickshell.env("PREVIEW_OUT")  // the folder frames are written to
  readonly property string wallpaper: Quickshell.env("PREVIEW_WALLPAPER")
  readonly property int fps: Number(Quickshell.env("PREVIEW_FPS") || 12)

  // Only what the Picker and the bar widget read from their Service; nothing here sends.
  QtObject {
    id: fakeService
    property var pending: []
    property var held: []
    property bool busy: false
    property var testSend: null
    property var handed: []
    function enqueue(books) { handed = books }
    function cancelPending() {}
    function sendTest(sender) {}
  }

  // What the bar widget reaches its Service through (bar.shell.serviceFor).
  function serviceFor(pluginId) { return pluginId === "sorydi3.kindle-send" ? fakeService : null }

  // The bar's face for a plugin widget, as Omarchy's bar gives it.
  PluginBarApi {
    id: barApi
    pluginId: "sorydi3.kindle-send"
    moduleName: "sorydi3.kindle-send"
    shell: shell
    foreground: Commons.Color.bar.text
    barForeground: Commons.Color.bar.text
    background: Commons.Color.bar.background
    urgent: Commons.Color.bar.active
    fontFamily: Style.font.family
    barSize: Style.bar.sizeHorizontal
    // The widget's left-click runs `omarchy-shell shell toggle sorydi3.kindle-send`.
    _run: function(command) {
      if (command !== "omarchy-shell shell toggle sorydi3.kindle-send") return
      if (picker.opened) picker.close()
      else picker.open("")
    }
  }

  P.Translator { id: tr }

  // The notification card's row, as Omarchy's notification server would hold it.
  property var note: null
  function post(text, urgency) {
    shell.note = {
      key: "demo", app: tr.t("app.name"), glyph: "\u{F02D}",
      urgency: urgency === "critical" ? 2 : urgency === "normal" ? 1 : 0,
      summary: text.headline, body: text.body, bodyRich: Markup.render(text.body),
      ts: Date.now() / 1000, duration: 0
    }
  }

  // --- The timeline: seconds -> what happens then -------------------------

  property int frame: 0
  readonly property real time: frame / fps
  readonly property int total: Math.round(16.6 * fps)

  // The key caption: what it says, and the frames it shows between.
  property string caption: ""
  property int captionFrom: -100
  property int captionUntil: -100
  function key(text, seconds) {
    shell.caption = text
    shell.captionFrom = shell.frame
    shell.captionUntil = shell.frame + Math.round((seconds || 0.9) * fps)
  }
  // The click ring on the bar icon.
  property int clickFrom: -100
  property point clickAt: Qt.point(0, 0)
  property int noteFrom: -100
  property int noteUntil: 100000

  function type(letter) {
    picker.filterText = picker.filterText + letter
    picker.selectedIndex = 0
    shell.key(picker.filterText, 0.9)
  }

  function press(down) {
    const button = shell.iconButton()
    if (down) {
      shell.clickFrom = shell.frame
      shell.clickAt = widget.mapToItem(stage, widget.width / 2, widget.height / 2)
    }
    if (button) button.heldButtons = down ? Qt.LeftButton : Qt.NoButton
  }
  function click() {
    shell.press(false)
    shell.iconButton().triggerPress(Qt.LeftButton)
  }
  // The BarIconButton inside the plugin's BarWidget.
  function iconButton() {
    for (let i = 0; i < widget.children.length; i++)
      if (typeof widget.children[i].triggerPress === "function") return widget.children[i]
    return null
  }

  readonly property var timeline: [
    [0.5, function() { shell.key("Click", 0.8); shell.press(true) }],
    [0.75, function() { shell.click(); return function() { return !picker.loading && picker.books.length > 0 } }],
    [1.7, function() { shell.type("a") }],
    [1.95, function() { shell.type("n") }],
    [2.2, function() { shell.type("d") }],
    [3.4, function() { shell.key("Esc"); picker.filterText = ""; picker.selectedIndex = 0 }],
    [4.2, function() { shell.key("Space"); picker.toggleMark(picker.current) }],
    [5.0, function() { shell.key("↓"); picker.select(1) }],
    [5.8, function() { shell.key("Tab", 1.2); picker.switchRoute(picker.current) }],
    [7.0, function() { shell.key("Space"); picker.toggleMark(picker.current) }],
    [8.2, function() {
      shell.key("Enter")
      picker.send()
      fakeService.busy = true
      shell.post(Feedback.progress(fakeService.handed, tr), "low")
      shell.noteFrom = shell.frame
    }],
    [9.3, function() {
      // What the Service would write once both are done: the email sent, the
      // USB Book copied and the Kindle ejected.
      const results = fakeService.handed.map(function(b) {
        return { name: b.name, result: b.route === Routes.USB ? "copied" : "sent" }
      })
      const s = Feedback.summary(results, { ejected: true }, tr)
      shell.post(s, s.urgency)
      fakeService.busy = false
    }],
    [11.9, function() { shell.noteUntil = shell.frame }],
    [12.1, function() { shell.key("Click", 0.8); shell.press(true) }],
    [12.35, function() { shell.click(); return function() { return !picker.loading && picker.books.length > 0 } }],
    [13.0, function() {
      shell.key("Ctrl+,", 1.0)
      picker.openSettings("")
      return function() { return picker.settingsValues.kindleAddress !== "" && picker.settingsPasswordStored }
    }],
    [15.2, function() { shell.key("Esc", 0.7); picker.leaveSettings() }],
    [15.9, function() { shell.key("Esc", 0.7); picker.close() }],
  ]

  // --- The scene -----------------------------------------------------------

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

      // A bar strip along the top holding the plugin's own bar widget.
      Rectangle {
        id: barStrip
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: barApi.barSize
        color: barApi.background

        P.BarWidget {
          id: widget
          bar: barApi
          anchors.right: parent.right
          anchors.rightMargin: Style.space(14)
          anchors.verticalCenter: parent.verticalCenter
        }
      }

      // The click: a ring that widens and fades around the bar icon, over the Picker as it opens.
      Rectangle {
        readonly property real age: (shell.frame - shell.clickFrom) / shell.fps
        z: 1
        visible: age >= 0 && age < 0.5
        width: Style.space(22) + age * Style.space(40)
        height: width
        radius: width / 2
        x: shell.clickAt.x - width / 2
        y: shell.clickAt.y - height / 2
        color: "transparent"
        border.width: Math.max(1, Style.space(2))
        border.color: Commons.Color.menu.selectedText
        opacity: 1 - age / 0.5
      }

      // The Picker, scrim and card, drawn into the scene (PreviewPanel.qml).
      P.Picker {
        id: picker
        anchors.fill: parent
        service: fakeService
      }

      // Omarchy's own notification card, sliding in under the bar.
      Item {
        readonly property real inAge: (shell.frame - shell.noteFrom) / shell.fps
        readonly property real outAge: (shell.frame - shell.noteUntil) / shell.fps
        readonly property real shown: Math.max(0, Math.min(1, inAge / 0.25, 1 - outAge / 0.3))
        visible: shell.note !== null && shown > 0
        opacity: shown
        anchors.top: barStrip.bottom
        anchors.right: parent.right
        anchors.topMargin: Style.gapsOut
        anchors.rightMargin: Style.gapsOut - (1 - shown) * Style.space(40)
        width: toast.width
        height: toast.height

        N.Toast {
          id: toast
          cardWidth: Style.space(400)
          sole: true
          expanded: true
          row: shell.note || ({})
        }
      }

      // The key caption: a keycap pill under the card, in the theme's menu colours.
      Rectangle {
        readonly property real inAge: (shell.frame - shell.captionFrom) / shell.fps
        readonly property real outAge: (shell.frame - shell.captionUntil) / shell.fps
        readonly property real shown: Math.max(0, Math.min(inAge >= 0 ? 1 : 0, 1 - outAge / 0.25))
        visible: shown > 0
        opacity: shown
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Style.space(26)
        width: Math.max(height * 1.6, captionText.implicitWidth + Style.space(36))
        height: captionText.implicitHeight + Style.space(14)
        radius: height / 2
        color: Commons.Color.menu.background
        border.width: Math.max(1, Style.space(2))
        border.color: Commons.Color.menu.selectedText

        Text {
          id: captionText
          anchors.centerIn: parent
          textFormat: Text.PlainText
          text: shell.caption
          color: Commons.Color.menu.text
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.title
        }
      }
    }
  }

  // --- Frame by frame ----------------------------------------------------------
  // Each frame: run what the timeline holds for it, wait while the Picker asks
  // kindle-send (plan, settings), let it draw, then grab it.

  property int next: 0           // the next timeline entry
  property var waitFor: null     // a condition the timeline waits on before grabbing
  property int settle: 0
  property bool grabbing: false
  property bool ran: false

  Timer {
    interval: Math.round(1000 / shell.fps)
    repeat: true
    running: true
    onTriggered: {
      if (shell.grabbing) return
      if (shell.waitFor) {
        if (!shell.waitFor()) return
        shell.waitFor = null
        shell.settle = 2
      }
      if (shell.settle > 0) { shell.settle -= 1; return }
      if (!shell.ran) {
        shell.ran = true
        while (shell.next < shell.timeline.length && Math.round(shell.timeline[shell.next][0] * shell.fps) <= shell.frame) {
          const wait = shell.timeline[shell.next][1]()
          shell.next += 1
          if (wait) { shell.waitFor = wait; return }
        }
      }
      shell.grabbing = true
      stage.grabToImage(function(result) {
        const name = shell.out + "/frame-" + String(shell.frame).padStart(4, "0") + ".png"
        if (!result.saveToFile(name)) { console.log("PREVIEW ERROR could not save", name); Qt.quit() }
        shell.frame += 1
        shell.ran = false
        shell.grabbing = false
        if (shell.frame >= shell.total) { console.log("PREVIEW SAVED", shell.out); Qt.quit() }
      }, Qt.size(stage.width * 2, stage.height * 2))
    }
  }
}
