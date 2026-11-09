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
  // Set a moment after loading starts, so a quick plan shows no flash of "Looking…".
  property bool loadingShown: false
  property bool setupNeeded: false
  // Why listing failed: "" | "missing" (no kindle-send) | "failed" | "slow".
  property string failure: ""
  property var books: []
  // path -> true for marked Books; path -> "email"|"usb" for Tab overrides.
  property var marked: ({})
  property var routes: ({})
  property string filterText: ""
  property int selectedIndex: 0
  // From `kindle-send plan`: the Book folders it scans and the Route labels.
  property var bookFolders: []
  property var routeLabels: ({})
  // Files from a Nautilus summon ({"files": [...]}); empty means the Book folders.
  property var payloadFiles: []
  readonly property bool payloadMode: payloadFiles.length > 0

  readonly property int rowHeight: Style.space(54)
  // Three text strengths, never multiplied together. Secondary stays readable
  // (4.5:1 or better in most Omarchy themes); dim is only for a Book its Route can't take.
  readonly property real secondaryOpacity: 0.72
  readonly property real hintOpacity: 0.5
  readonly property real dimOpacity: 0.4

  readonly property var rows: Rows.filter(books, filterText)
  // Pending Sends held by the Service, shown as one "N Books waiting for Kindle" line on top.
  readonly property var pending: service && service.pending ? service.pending : []
  readonly property var listRows: Pending.withWaiting(rows, pending)
  readonly property var current: listRows.length > 0 ? listRows[Math.min(selectedIndex, listRows.length - 1)] : null
  // Footer text: what Enter sends, and which marked Books their Route can't take.
  readonly property var sendSummary: Rows.footer(books, marked, routes, current, routeLabels)
  // Setup, a failure, loading, or an empty list: what shows instead of the list (null: the list).
  readonly property var screen: Rows.screen({
    loading: loading, setupNeeded: setupNeeded, failure: failure, payloadCount: payloadFiles.length,
    books: books.length, rows: rows.length, waiting: pending.length, filterText: filterText,
    bookFolders: bookFolders })
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
    // plan reruns on every open, so settings rewritten by setup show at once.
    root.list()
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  function close() {
    root.opened = false
    planner.running = false
    responseTimer.stop()
    loadingDelay.stop()
  }

  // --- Asking kindle-send -------------------------------------------------

  function list() {
    root.failure = ""
    root.loading = true
    root.loadingShown = false
    loadingDelay.restart()
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
    root.bookFolders = parsed.bookFolders
    root.routeLabels = parsed.routeLabels
    if (root.payloadMode) root.marked = Rows.allMarked(parsed.books)
    if (exitCode !== 0 && parsed.books.length === 0 && !parsed.setupNeeded)
      root.failure = "failed"
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
      root.failure = "missing"
    }
    onExited: function(exitCode) { root.listed(exitCode) }
  }

  Timer {
    id: responseTimer
    interval: 10000
    onTriggered: if (planner.running) {
      planner.running = false
      root.loading = false
      root.failure = "slow"
    }
  }

  Timer {
    id: loadingDelay
    interval: 400
    onTriggered: root.loadingShown = root.loading
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

  // Tab on a marked Book switches every marked Book.
  function switchRoute(book) {
    root.routes = Rows.switchRoutes(root.books, root.marked, root.routes, book)
  }

  // Enter: the marked Books, or the highlighted one if none are marked.
  function send() { root.hand(Rows.toSend(root.books, root.marked, root.routes, root.current)) }

  // Double-click: just this Book, whatever else is marked.
  function sendOne(book) { root.hand(Rows.toSend(root.books, {}, root.routes, book)) }

  // Hands the Books to the Service and closes at once.
  function hand(chosen) {
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

      MouseArea { anchors.fill: parent; onClicked: if (root.screen && root.screen.enter === "setup") root.runSetup() }

      Item {
        id: keyCatcher
        anchors.fill: parent
        focus: true

        Keys.priority: Keys.BeforeItem
        Keys.onPressed: function(event) {
          event.accepted = true
          const enter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
          const screen = root.screen
          if (event.key === Qt.Key_Escape) {
            if (root.filterText) root.filterText = ""
            else root.close()
          } else if (enter) {
            const action = screen ? screen.enter : "send"
            if (action === "send") root.send()
            else if (action === "setup") root.runSetup()
            else if (action === "retry") root.list()
            else if (action === "close") root.close()
          } else if (screen && !screen.typing) {
            // Setup, failures and empty folders take only Enter and Esc.
          } else if (event.key === Qt.Key_Space) root.toggleMark(root.current)
          else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) root.switchRoute(root.current)
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
          visible: !root.screen || root.screen.typing
          width: parent.width
          height: Style.space(34)
          textFormat: Text.PlainText
          text: root.filterText || "Send to Kindle…"
          color: Color.menu.text
          opacity: root.filterText ? 1 : 0.58  // the shell's own placeholder strength
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.heading
          elide: Text.ElideRight
          verticalAlignment: Text.AlignVCenter
        }

        // What Enter will send, then the keys that work here.
        Column {
          id: footer
          anchors.bottom: parent.bottom
          width: parent.width
          spacing: Style.space(6)

          Text {
            visible: !root.screen && text !== ""
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            text: root.sendSummary.status
            color: Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
            elide: Text.ElideRight
          }
          Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            textFormat: Text.PlainText
            text: root.screen ? root.screen.keys : Rows.hints(root.current, root.sendSummary.enter, root.filterText)
            color: Color.menu.text
            opacity: root.hintOpacity
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.bodySmall
            elide: Text.ElideRight
          }
        }

        ListView {
          id: list
          visible: !root.screen
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
              // An empty box stays plain text, readable on the highlighted row too.
              color: row.isMarked || row.waiting ? row.ink : Color.menu.text
              opacity: row.isMarked || row.waiting ? 1 : root.secondaryOpacity
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
                text: Rows.routeLabel(row.route, root.routeLabels)
                color: row.ink
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.caption
              }
            }

            Column {
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
                // Dimmed when the chosen Route can't take this Book; the details line says why.
                opacity: row.waiting || Rows.routeTakes(row.modelData, row.route) ? 1 : root.dimOpacity
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.title
                elide: Text.ElideMiddle
              }
              Text {
                width: parent.width
                textFormat: Text.PlainText
                text: row.waiting ? row.modelData.details : Rows.details(row.modelData, row.route, Date.now(), root.routeLabels)
                // Plain text color even on the highlighted row, as the shell's own menu does.
                color: Color.menu.text
                opacity: root.secondaryOpacity
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
              // The two clicks before it mark and unmark, leaving the marks as they were.
              onDoubleClicked: root.sendOne(row.modelData)
            }
          }
        }

        // Setup, a failure, loading, no Books or no matches. Loading shows after a short delay.
        Column {
          anchors.centerIn: parent
          width: parent.width
          spacing: Style.space(8)
          visible: root.screen !== null && (!root.loading || root.loadingShown)

          Text {
            anchors.horizontalCenter: parent.horizontalCenter
            // A cog for setup, a warning for failures, a book otherwise.
            text: root.setupNeeded ? "\u{F0493}" : root.failure ? "\u{F0026}" : "\u{F02D}"
            color: Color.menu.selectedText
            opacity: root.secondaryOpacity
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.displayLarge
          }
          Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: root.screen ? root.screen.message : ""
            color: Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.title
          }
          Text {
            visible: text !== ""
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: root.screen ? root.screen.detail : ""
            color: Color.menu.text
            opacity: root.secondaryOpacity
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
        }
      }
    }
  }
}
