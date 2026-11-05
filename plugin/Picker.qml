// The Picker (spec §4): lists Books from the Book folders, newest first.
// Space marks, Tab switches the Route, Enter hands the marked (or highlighted)
// Books to the Service and closes at once, Esc closes. It never handles the
// password: kindle-send reads the keyring itself.
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui
import "Rows.js" as Rows
import "Pending.js" as Pending

Item {
  id: root

  // Injected by the shell: this plugin's Service.
  property var service: null

  property bool opened: false
  property bool loading: false
  property bool setupNeeded: false
  property string failure: ""
  property var books: []
  // path -> true for marked Books; path -> "email"|"usb" for Tab overrides.
  property var marked: ({})
  property var routes: ({})
  property string filterText: ""
  property int selectedIndex: 0
  property var bookFolders: Rows.DEFAULT_FOLDERS
  // Files from a Nautilus summon ({"files": [...]}); empty means the Book folders.
  property var payloadFiles: []
  readonly property bool payloadMode: payloadFiles.length > 0

  readonly property int rowHeight: Style.space(54)
  readonly property string shellJson: {
    const override = Quickshell.env("KINDLE_SEND_SHELL_JSON")
    if (override) return override
    const config = Quickshell.env("XDG_CONFIG_HOME") || (Quickshell.env("HOME") + "/.config")
    return config + "/omarchy/shell.json"
  }

  readonly property var rows: Rows.filter(books, filterText)
  // Pending Sends held by the Service, shown as one "N Books waiting for Kindle" line on top.
  readonly property var pending: service && service.pending ? service.pending : []
  readonly property var listRows: Pending.withWaiting(rows, pending)
  readonly property var current: listRows.length > 0 ? listRows[Math.min(selectedIndex, listRows.length - 1)] : null
  readonly property int markedCount: Object.keys(marked).length
  onListRowsChanged: selectedIndex = Math.max(0, Math.min(selectedIndex, listRows.length - 1))

  function open(payloadJson) {
    root.opened = true
    root.filterText = ""
    root.selectedIndex = 0
    root.marked = {}
    root.routes = {}
    root.books = []
    root.failure = ""
    root.setupNeeded = false
    root.payloadFiles = Rows.payloadFiles(payloadJson)
    root.list()
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  function close() {
    root.opened = false
    planner.running = false
    responseTimer.stop()
  }

  // --- Asking kindle-send -------------------------------------------------

  function list() {
    root.loading = true
    planner.lines = []
    planner.didStart = false
    // close() stops the planner, so it is idle here and picks up the new command.
    planner.command = Rows.planCommand(root.payloadFiles)
    if (!planner.running) planner.running = true
    responseTimer.restart()
  }

  function listed(exitCode) {
    responseTimer.stop()
    if (!root.loading) return
    root.loading = false
    const parsed = Rows.fromPlan(planner.lines)
    root.setupNeeded = parsed.setupNeeded
    root.books = parsed.books
    if (root.payloadMode) root.marked = Rows.allMarked(parsed.books)
    if (exitCode !== 0 && parsed.books.length === 0 && !parsed.setupNeeded)
      root.failure = "kindle-send plan failed (exit " + exitCode + ")."
  }

  Process {
    id: planner
    property var lines: []
    property bool didStart: false
    command: Rows.planCommand([])
    stdout: SplitParser {
      onRead: function(line) {
        try { planner.lines = planner.lines.concat([JSON.parse(line)]) } catch (e) {}
      }
    }
    onStarted: didStart = true
    // A program that cannot be found never starts and never exits.
    onRunningChanged: if (!running && !didStart && root.loading) {
      root.loading = false
      root.failure = "kindle-send is not installed. Run scripts/install.sh."
    }
    onExited: function(exitCode) { root.listed(exitCode) }
  }

  Timer {
    id: responseTimer
    interval: 10000
    onTriggered: if (planner.running) {
      planner.running = false
      root.loading = false
      root.failure = "kindle-send plan did not answer."
    }
  }

  // The Book folders, only to name them in the empty state.
  FileView {
    path: root.shellJson
    watchChanges: true
    printErrors: false
    onLoaded: root.bookFolders = Rows.foldersFromShellJson(text())
    onFileChanged: reload()
  }

  // --- Actions ------------------------------------------------------------

  function routeOf(book) { return Rows.routeOf(book, root.routes) }

  function toggleMark(book) {
    if (!book || book.waiting) return
    const next = Object.assign({}, root.marked)
    if (next[book.path]) delete next[book.path]
    else next[book.path] = true
    root.marked = next
  }

  function switchRoute(book) {
    if (!book || book.waiting) return
    const next = Object.assign({}, root.routes)
    next[book.path] = root.routeOf(book) === "email" ? "usb" : "email"
    root.routes = next
  }

  function send() {
    const chosen = Rows.toSend(root.books, root.marked, root.routes, root.current)
    if (chosen.length === 0) return
    if (root.service) root.service.enqueue(chosen)
    root.close()
  }

  function runSetup() {
    Util.execArgv(["omarchy-launch-floating-terminal-with-presentation", "kindle-send", "setup"])
    root.close()
  }

  // Delete on the waiting line cancels every Pending Send.
  function cancelWaiting(row) {
    if (row && row.waiting && root.service) root.service.cancelPending()
  }

  function select(delta) {
    if (root.listRows.length === 0) return
    root.selectedIndex = Math.max(0, Math.min(root.listRows.length - 1, root.selectedIndex + delta))
  }

  // --- Drawing ------------------------------------------------------------

  // A layer-shell window needs a compositor, which qmllint does not have.
  // qmllint disable uncreatable-type
  PanelWindow {
    // qmllint enable uncreatable-type
    id: panel
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "kindle-send-picker"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    exclusionMode: ExclusionMode.Ignore

    Rectangle { anchors.fill: parent; color: Color.menu.scrim }

    MouseArea { anchors.fill: parent; onClicked: root.close() }

    BorderSurface {
      id: card
      anchors.centerIn: parent
      width: Math.min(Style.space(640), parent.width - Style.gapsOut * 2)
      height: Math.min(Style.space(520), parent.height - Style.gapsOut * 2)
      radius: Style.cornerRadius
      color: Color.menu.background
      borderSpec: Border.surfaceSpec("menu", "border", Color.menu.border, Math.max(1, Style.space(2)))
      padding: Style.spacing.panelPadding

      MouseArea { anchors.fill: parent; onClicked: if (root.setupNeeded) root.runSetup() }

      Item {
        id: keyCatcher
        anchors.fill: parent
        focus: true

        Keys.priority: Keys.BeforeItem
        Keys.onPressed: function(event) {
          event.accepted = true
          const enter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
          if (root.setupNeeded || root.failure) {
            if (event.key === Qt.Key_Escape) root.close()
            else if (enter && root.setupNeeded) root.runSetup()
            else if (enter) root.close()
          } else if (event.key === Qt.Key_Escape) {
            if (root.filterText) root.filterText = ""
            else root.close()
          } else if (event.key === Qt.Key_Space) root.toggleMark(root.current)
          else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) root.switchRoute(root.current)
          else if (enter) root.send()
          else if (event.key === Qt.Key_Delete) root.cancelWaiting(root.current)
          else if (Util.editsFilter(event, root.filterText)) {
            root.filterText = Util.editedFilter(event, root.filterText)
            root.selectedIndex = 0
          } else if (event.key === Qt.Key_Up) root.select(-1)
          else if (event.key === Qt.Key_Down) root.select(1)
          else if (event.key === Qt.Key_PageUp) root.select(-6)
          else if (event.key === Qt.Key_PageDown) root.select(6)
          else if (event.text && event.text.length === 1 && event.text.charCodeAt(0) > 32 && event.text.charCodeAt(0) !== 127) {
            root.filterText = root.filterText + event.text
            root.selectedIndex = 0
          } else event.accepted = false
        }
      }

      Item {
        anchors.fill: parent
        anchors.topMargin: card.contentTopInset
        anchors.rightMargin: card.contentRightInset
        anchors.bottomMargin: card.contentBottomInset
        anchors.leftMargin: card.contentLeftInset

        Text {
          id: search
          visible: !root.setupNeeded && !root.failure
          width: parent.width
          height: Style.space(34)
          textFormat: Text.PlainText
          text: root.filterText || "Send to Kindle…"
          color: Color.menu.text
          opacity: root.filterText ? 1 : 0.58
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.heading
          elide: Text.ElideRight
          verticalAlignment: Text.AlignVCenter
        }

        Text {
          id: footer
          visible: !root.setupNeeded && !root.failure
          anchors.bottom: parent.bottom
          anchors.horizontalCenter: parent.horizontalCenter
          width: Math.min(implicitWidth, parent.width)
          textFormat: Text.PlainText
          text: (root.markedCount > 0 ? root.markedCount + " marked      " : "")
            + "Space  Mark      Tab  Route      Enter  Send      Esc  Close"
          color: Color.menu.text
          opacity: 0.5
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.bodySmall
          elide: Text.ElideRight
        }

        ListView {
          id: list
          visible: !root.setupNeeded && !root.failure
          anchors.top: search.bottom
          anchors.topMargin: Style.spacing.md
          anchors.bottom: footer.top
          anchors.bottomMargin: Style.spacing.lg
          anchors.left: parent.left
          anchors.right: parent.right
          model: root.listRows
          currentIndex: root.selectedIndex
          clip: true
          spacing: Style.space(4)
          boundsBehavior: Flickable.StopAtBounds

          delegate: Rectangle {
            id: row
            required property int index
            required property var modelData
            readonly property bool hasCursor: index === root.selectedIndex
            readonly property bool waiting: modelData.waiting === true
            readonly property bool isMarked: !waiting && root.marked[modelData.path] === true
            readonly property string route: waiting ? "" : root.routeOf(modelData)
            readonly property color ink: hasCursor ? Color.menu.selectedText : Color.menu.text

            width: ListView.view.width
            height: root.rowHeight
            radius: Style.cornerRadius
            color: hasCursor ? Color.menu.selectedBackground : "transparent"

            Text {
              id: mark
              anchors.left: parent.left
              anchors.leftMargin: Style.space(12)
              anchors.verticalCenter: parent.verticalCenter
              width: Style.space(24)
              // A clock on the waiting line, a checkbox on Books.
              text: row.waiting ? "\u{F0954}" : row.isMarked ? "\u{F0132}" : "\u{F0131}"
              color: row.ink
              opacity: row.isMarked || row.waiting ? 1 : 0.4
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.title
            }

            Rectangle {
              id: badge
              visible: !row.waiting
              anchors.right: parent.right
              anchors.rightMargin: Style.space(12)
              anchors.verticalCenter: parent.verticalCenter
              width: badgeText.implicitWidth + Style.space(16)
              height: badgeText.implicitHeight + Style.space(6)
              radius: height / 2
              color: "transparent"
              border.color: row.ink
              border.width: 1

              Text {
                id: badgeText
                anchors.centerIn: parent
                text: Rows.routeLabel(row.route)
                color: row.ink
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.caption
              }
            }

            Column {
              // Dimmed when the chosen Route can't take this Book.
              opacity: row.waiting || Rows.routeTakes(row.modelData, row.route) ? 1 : 0.4
              anchors.left: mark.right
              anchors.leftMargin: Style.space(8)
              anchors.right: badge.left
              anchors.rightMargin: Style.space(12)
              anchors.verticalCenter: parent.verticalCenter
              spacing: Style.space(2)

              Text {
                width: parent.width
                textFormat: Text.PlainText
                text: row.modelData.name
                color: row.ink
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.title
                elide: Text.ElideMiddle
              }
              Text {
                width: parent.width
                textFormat: Text.PlainText
                text: row.waiting ? row.modelData.details : Rows.details(row.modelData, row.route, Date.now())
                color: row.ink
                opacity: 0.6
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.bodySmall
                elide: Text.ElideRight
              }
            }

            MouseArea {
              anchors.fill: parent
              hoverEnabled: true
              onPositionChanged: root.selectedIndex = row.index
              onClicked: root.toggleMark(row.modelData)
            }
          }
        }

        // Setup needed, a failure, no Books, or no matches. Nothing while loading.
        Column {
          anchors.centerIn: parent
          width: parent.width
          spacing: Style.space(8)
          visible: root.setupNeeded || root.failure !== "" || (!root.loading && root.rows.length === 0)

          Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.setupNeeded ? "\u{F0493}" : "\u{F02D}"
            color: Color.menu.selectedText
            opacity: 0.8
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.displayLarge
          }
          Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: root.setupNeeded ? "Set up Send to Kindle"
              : root.failure ? root.failure
              : root.books.length === 0 && root.payloadMode ? "None of these files can be sent to a Kindle."
              : root.books.length === 0 ? Rows.emptyMessage(root.bookFolders)
              : "No matches for “" + root.filterText + "”"
            color: Color.menu.text
            opacity: 0.8
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.title
          }
          Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            visible: root.setupNeeded || (!root.failure && !root.payloadMode && root.books.length === 0)
            text: root.setupNeeded ? "Enter  Start setup      Esc  Close"
              : "To search other folders, rerun setup: kindle-send setup"
            color: Color.menu.text
            opacity: 0.5
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.bodySmall
          }
        }
      }
    }
  }
}
