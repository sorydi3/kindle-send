// The Picker (spec §4): lists Books from the Book folders, newest first.
// Space marks, Tab switches the Route, Enter hands the marked (or highlighted)
// Books to the Service and closes at once, Esc closes. Ctrl+, or the cog opens
// Settings in the card (spec §9); kindle-send checks and writes them. While
// setup is needed the Picker opens straight into Settings.
import QtQuick
import QtQuick.Dialogs
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui
import "Rows.js" as Rows
import "Pending.js" as Pending
import "Settings.js" as SettingsForm
import "Program.js" as Program

Item {
  id: root

  // Injected by the shell: this plugin's Service.
  property var service: null

  // The kindle-send bundled in the plugin folder; every command runs it, never one from PATH (spec §17).
  readonly property string kindleSend: Program.path(Qt.resolvedUrl("bin/kindle-send"))

  property bool opened: false
  property bool loading: false
  // Set a moment after loading starts, so a quick plan shows no flash of "Looking…".
  property bool loadingShown: false
  // From plan: a setting or the app password is missing, so the Picker opens into Settings.
  property bool setupNeeded: false
  property var setupMissing: []
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

  // --- Settings form state (spec §9). While open, the Book list takes no keys.
  property bool settingsOpen: false
  // The form's values (strings), and what was loaded or last saved, to tell edits apart.
  property var settingsValues: SettingsForm.fromSettings(null)
  property var settingsBaseline: SettingsForm.fromSettings(null)
  // kindle-send settings says whether an app password is stored; the password itself never reaches the form.
  property bool settingsPasswordStored: false
  // What setup still needs (kindle-send settings): titles the form, flags fields, makes Esc close.
  property var settingsMissing: []
  readonly property bool settingsSetup: SettingsForm.setupNeeded(settingsMissing)
  // field key -> problem message from the last save, cleared as each field is edited.
  property var settingsProblems: ({})
  property string settingsStatus: ""
  property string settingsFocus: ""
  property bool settingsSaving: false
  // Something was saved since Settings opened, so the Book list is planned again on the way back.
  property bool settingsSavedSinceOpen: false
  readonly property bool settingsChanged: SettingsForm.changed(settingsValues, settingsBaseline)
  // The form kept while the Picker steps aside for a browser or dialog; the next open returns to it.
  property var settingsAside: null
  // Ctrl+T started a test send from this form, so its status line follows the Service's testSend.
  property bool settingsTesting: false

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
    loading: loading, failure: failure, payloadCount: payloadFiles.length,
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
    root.settingsOpen = false
    root.payloadFiles = Rows.payloadFiles(payloadJson)
    // plan reruns on every open, so settings rewritten by setup show at once.
    root.list()
    // The menu's Settings entry, a failure notification's click, a form that stepped aside, or the list (spec §10, §13, §14).
    const intent = SettingsForm.openIntent(payloadJson, root.settingsAside)
    root.settingsAside = null
    if (intent.to === "settings") root.openSettings(intent.focus, intent.problems)
    else if (intent.to === "returned") root.returnToSettings(intent.form)
    else Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  function close() {
    root.opened = false
    root.settingsOpen = false
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
    planner.command = Rows.planCommand(root.kindleSend, root.payloadFiles)
    if (!planner.running) planner.running = true
    responseTimer.restart()
  }

  function listed(exitCode) {
    responseTimer.stop()
    if (!root.loading) return
    root.loading = false
    const parsed = Rows.fromPlan(planner.lines)
    root.setupNeeded = parsed.setupNeeded
    root.setupMissing = parsed.missing
    root.books = parsed.books
    root.bookFolders = parsed.bookFolders
    root.routeLabels = parsed.routeLabels
    if (root.payloadMode) root.marked = Rows.allMarked(parsed.books)
    if (exitCode !== 0 && parsed.books.length === 0 && !parsed.setupNeeded)
      root.failure = "failed"
    // No usable Book list yet: straight into Settings (spec §4, Setup needed).
    if (parsed.setupNeeded) root.openSettings("")
  }

  Process {
    id: planner
    property var lines: []
    property bool didStart: false
    command: Rows.planCommand(root.kindleSend, [])
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

  // --- Settings ---------------------------------------------------------

  // Opens Settings on `focusKey` (a field key; "" for the first field), with
  // `problems` (key -> message) shown if given. The one way in: Ctrl+, and the
  // cog, setup needed, the empty Book list (Book folders), a failure
  // notification (the field at fault). Already open, it changes nothing.
  function openSettings(focusKey, problems) {
    if (root.settingsOpen) return
    root.settingsOpen = true
    root.settingsProblems = problems || {}
    root.settingsStatus = ""
    root.settingsTesting = false
    root.settingsSavedSinceOpen = false
    root.settingsPasswordStored = false
    // plan's word until kindle-send settings answers, so the title doesn't flicker.
    root.settingsMissing = root.setupNeeded ? root.setupMissing : []
    root.settingsValues = SettingsForm.fromSettings(null)
    root.settingsBaseline = root.settingsValues
    root.loadSettings(true)
    const focus = focusKey || SettingsForm.fields()[0].key
    Qt.callLater(function() { root.focusSettingsField(focus) })
  }

  // Esc: back to the Book list, unsaved edits dropped; while setup is needed
  // there is no Book list yet, so it closes the Picker.
  function leaveSettings() {
    if (SettingsForm.escCloses(root.settingsMissing)) root.close()
    else root.closeSettings()
  }

  function closeSettings() {
    root.settingsOpen = false
    root.settingsValues = root.settingsBaseline
    keyCatcher.forceActiveFocus()
    if (root.settingsSavedSinceOpen) root.list()
  }

  // replaceValues: show what was read in the fields (on opening, and after a
  // save, so an emptied Book folders field shows the defaults it saved as).
  function loadSettings(replaceValues) {
    settingsReader.replaceValues = replaceValues
    settingsReader.line = null
    settingsReader.didStart = false
    if (!settingsReader.running) settingsReader.running = true
  }

  function settingsLoaded(exitCode) {
    const line = settingsReader.line
    if (exitCode !== 0 || !line) {
      root.settingsStatus = "Couldn't read the Settings. Run kindle-send settings in a terminal to see why."
      return
    }
    root.settingsBaseline = SettingsForm.fromSettings(line)
    root.settingsPasswordStored = line.appPasswordStored === true
    root.settingsMissing = SettingsForm.missing(line)
    if (settingsReader.replaceValues) root.settingsValues = root.settingsBaseline
  }

  function editSetting(key, text) {
    const next = Object.assign({}, root.settingsValues)
    next[key] = text
    root.settingsValues = next
    root.settingsProblems = SettingsForm.edited(root.settingsProblems, key)
  }

  // Enter, from any field: kindle-send save checks and writes; values go over stdin.
  function saveSettings() {
    if (root.settingsSaving) return
    root.settingsSaving = true
    root.settingsStatus = SettingsForm.savingStatus(root.settingsValues)
    saver.result = null
    saver.didStart = false
    saver.payload = JSON.stringify(SettingsForm.toSave(root.settingsValues))
    saver.running = true
  }

  function settingsSaved(exitCode) {
    root.settingsSaving = false
    saver.payload = ""  // it may hold the app password if save never started
    const result = saver.result
    if (exitCode !== 0 || !result) {
      root.settingsStatus = "Couldn't save. Run kindle-send save in a terminal to see why."
      return
    }
    root.settingsProblems = SettingsForm.byField(result.problems)
    root.settingsStatus = SettingsForm.status(result)
    const first = SettingsForm.firstProblem(result.problems)
    if (first) root.focusSettingsField(first)
    if (result.saved) {
      root.settingsSavedSinceOpen = true
      root.loadSettings(true)
    }
  }

  // --- Stepping aside: a link (or the folder chooser) shows over a closed Picker.
  // stepAside() keeps the form, unsaved values included, and closes; the next
  // open() comes back to it through returnToSettings().

  function stepAside() {
    root.settingsAside = SettingsForm.stepAside({
      values: root.settingsValues, baseline: root.settingsBaseline,
      problems: root.settingsProblems, status: root.settingsStatus,
      focus: root.settingsFocus, savedSinceOpen: root.settingsSavedSinceOpen,
      passwordStored: root.settingsPasswordStored, missing: root.settingsMissing,
      testing: root.settingsTesting })
    root.close()
  }

  function returnToSettings(back) {
    root.settingsOpen = true
    root.settingsValues = back.values
    root.settingsBaseline = back.baseline
    root.settingsProblems = back.problems || {}
    root.settingsStatus = back.status || ""
    root.settingsSavedSinceOpen = back.savedSinceOpen === true
    root.settingsPasswordStored = back.passwordStored === true
    root.settingsMissing = back.missing || []
    root.settingsTesting = back.testing === true
    // A test send may have finished while the Picker was closed.
    if (root.settingsTesting) root.showTestSend()
    const focus = back.focus || SettingsForm.fields()[0].key
    Qt.callLater(function() { root.focusSettingsField(focus) })
  }

  // --- Test send (spec §9): Ctrl+T, only once everything is saved. The Picker
  // stays in Settings; its status line follows the Service's testSend.

  function sendTestBook() {
    const testSend = root.service ? root.service.testSend : null
    const k = SettingsForm.testKey(root.settingsSetup, root.settingsChanged || root.settingsSaving, testSend)
    if (!k.send || !root.service) {
      root.settingsStatus = k.status
      return
    }
    root.settingsTesting = true
    root.service.sendTest(root.settingsBaseline.senderAddress)
  }

  function showTestSend() {
    const o = SettingsForm.testOutcome(root.service ? root.service.testSend : null)
    root.settingsStatus = o.status
    root.settingsProblems = Object.assign({}, root.settingsProblems, o.problems)
    const first = Object.keys(o.problems)[0]
    if (first) root.focusSettingsField(first)
  }

  Connections {
    target: root.service
    ignoreUnknownSignals: true
    function onTestSendChanged() {
      if (root.settingsOpen && root.settingsTesting) root.showTestSend()
    }
  }

  // Ctrl+O, or a click on the help line: the field's page in the browser.
  function openLink(key) {
    const argv = SettingsForm.browserArgv(key)
    if (argv.length === 0) return
    Util.execArgv(argv)
    root.stepAside()
  }

  // Ctrl+B on Book folders, or Browse…: the system folder chooser (FolderDialog,
  // the native GTK chooser in omarchy-shell) over a closed Picker. The Picker
  // comes back to Book folders whether a folder was picked or not.
  function browseFolder() {
    root.settingsFocus = "bookFolders"
    root.stepAside()
    folderDialog.open()
  }

  // url: the picked folder, or "" on Cancel. open() first: it restores the
  // kept form, which the folder is then appended to.
  function folderBrowsed(url) {
    root.open("")
    if (!url) return
    const folder = SettingsForm.chosenFolder(url, Quickshell.env("HOME"))
    root.editSetting("bookFolders", SettingsForm.withFolder(root.settingsValues.bookFolders, folder))
  }

  FolderDialog {
    id: folderDialog
    title: "Add a Book folder"
    currentFolder: "file://" + Quickshell.env("HOME")
    onAccepted: root.folderBrowsed(String(selectedFolder))
    onRejected: root.folderBrowsed("")
  }

  function focusSettingsField(key) {
    const keys = SettingsForm.fields().map(function(f) { return f.key })
    const item = settingsFields.itemAt(keys.indexOf(key))
    if (item) item.input.forceActiveFocus()
  }

  Process {
    id: settingsReader
    property var line: null
    property bool didStart: false
    property bool replaceValues: true
    command: [root.kindleSend, "settings"]
    stdout: SplitParser {
      onRead: function(text) {
        try { settingsReader.line = JSON.parse(text) } catch (e) {}
      }
    }
    onStarted: didStart = true
    onRunningChanged: if (!running && !didStart) root.settingsLoaded(1)
    onExited: function(exitCode) { root.settingsLoaded(exitCode) }
  }

  // The form's values reach kindle-send on stdin, one JSON line, never argv.
  Process {
    id: saver
    property string payload: ""
    property var result: null
    property bool didStart: false
    command: [root.kindleSend, "save"]
    stdinEnabled: true
    stdout: SplitParser {
      onRead: function(text) {
        try { saver.result = JSON.parse(text) } catch (e) {}
      }
    }
    onStarted: {
      didStart = true
      write(payload + "\n")
      payload = ""
    }
    onRunningChanged: if (!running && !didStart) root.settingsSaved(1)
    onExited: function(exitCode) { root.settingsSaved(exitCode) }
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

      // Swallows clicks on the card so they don't reach the scrim, which closes the Picker.
      MouseArea { anchors.fill: parent }

      Item {
        id: keyCatcher
        anchors.fill: parent
        focus: true
        // While Settings are open the Book list takes no keys: Enter here would send a Book.
        enabled: !root.settingsOpen

        Keys.priority: Keys.BeforeItem
        Keys.onPressed: function(event) {
          event.accepted = true
          if (root.settingsOpen) return
          const enter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
          const screen = root.screen
          if (event.key === Qt.Key_Escape) {
            if (root.filterText) root.filterText = ""
            else root.close()
          } else if (SettingsForm.opensSettings(event.key, event.modifiers)) {
            if (!screen || screen.settings) root.openSettings("")
          } else if (enter) {
            const action = screen ? screen.enter : "send"
            if (action === "send") root.send()
            else if (action === "settings") root.openSettings(screen.field)
            else if (action === "retry") root.list()
            else if (action === "close") root.close()
          } else if (screen && !screen.typing) {
            // Failures and empty folders take only Enter and Esc.
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
          visible: !root.settingsOpen && (!root.screen || root.screen.typing)
          width: parent.width - cog.width - Style.space(8)
          height: Style.space(34)
          textFormat: Text.PlainText
          text: root.filterText || "Books to Kindle…"
          color: Color.menu.text
          opacity: root.filterText ? 1 : 0.58  // the shell's own placeholder strength
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.heading
          elide: Text.ElideRight
          verticalAlignment: Text.AlignVCenter
        }

        // Opens Settings, like Ctrl+, does.
        Text {
          id: cog
          visible: !root.settingsOpen && (!root.screen || root.screen.settings)
          anchors.right: parent.right
          anchors.verticalCenter: search.verticalCenter
          text: "\u{F0493}"
          color: Color.menu.text
          opacity: cogMouse.containsMouse ? 1 : root.secondaryOpacity
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.title

          MouseArea {
            id: cogMouse
            anchors.fill: parent
            anchors.margins: -Style.space(6)
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openSettings("")
          }
        }

        // What Enter will send, then the keys that work here.
        Column {
          id: footer
          visible: !root.settingsOpen
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
          visible: !root.settingsOpen && !root.screen
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

        // A failure, loading, no Books or no matches. Loading shows after a short delay.
        Column {
          id: stateView
          anchors.centerIn: parent
          width: parent.width
          spacing: Style.space(8)
          visible: !root.settingsOpen && root.screen !== null && (!root.loading || root.loadingShown)

          Text {
            anchors.horizontalCenter: parent.horizontalCenter
            // A warning for failures, a book otherwise.
            text: root.failure ? "\u{F0026}" : "\u{F02D}"
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

        // Where Enter opens Settings, clicking the message does too; the rest of the card doesn't.
        MouseArea {
          anchors.fill: stateView
          visible: stateView.visible && root.screen !== null && root.screen.enter === "settings"
          cursorShape: Qt.PointingHandCursor
          onClicked: root.openSettings(root.screen.field)
        }

        // Settings (spec §9): one form over the Book list. Its own keys only:
        // Tab/Shift+Tab move between fields, Enter saves, Ctrl+O opens the
        // focused field's link, Ctrl+B on Book folders browses, Ctrl+T sends a
        // test Book once everything is saved, Esc goes back
        // (or closes the Picker while setup is needed).
        FocusScope {
          id: settingsForm
          anchors.fill: parent
          visible: root.settingsOpen
          enabled: root.settingsOpen
          focus: root.settingsOpen

          Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape) {
              event.accepted = true
              root.leaveSettings()
            } else if (SettingsForm.opensLink(event.key, event.modifiers)) {
              event.accepted = true
              root.openLink(root.settingsFocus)
            } else if (SettingsForm.opensBrowse(event.key, event.modifiers) && SettingsForm.browses(root.settingsFocus)) {
              event.accepted = true
              root.browseFolder()
            } else if (SettingsForm.opensTestSend(event.key, event.modifiers)) {
              event.accepted = true
              root.sendTestBook()
            } else event.accepted = false
          }

          // Clicks on the form stay off the Book list underneath.
          MouseArea { anchors.fill: parent }

          Column {
            width: parent.width
            spacing: Style.space(12)

            Text {
              text: SettingsForm.title(root.settingsMissing)
              color: Color.menu.text
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.heading
            }

            Repeater {
              id: settingsFields
              model: SettingsForm.fields()
              delegate: Column {
                id: entry
                required property var modelData
                required property int index
                property alias input: input
                readonly property var line: SettingsForm.helpLine(modelData, root.settingsProblems)
                // The help line is link text when the field has a page and no problem covers it.
                readonly property bool linked: !line.problem && SettingsForm.link(modelData.key) !== ""
                width: parent.width
                spacing: Style.space(4)

                // The label, with "· needed" beside it in the accent color while the value is missing.
                Row {
                  spacing: Style.space(6)

                  Text {
                    text: entry.modelData.label
                    color: Color.menu.text
                    font.family: Style.font.menuFamily
                    font.pixelSize: Style.font.body
                  }
                  Text {
                    visible: text !== ""
                    text: SettingsForm.flag(entry.modelData.key, root.settingsMissing, root.settingsValues,
                                            root.settingsBaseline)
                    color: Color.menu.selectedText
                    font.family: Style.font.menuFamily
                    font.pixelSize: Style.font.body
                  }
                }
                // The field, with Browse… beside it on Book folders.
                Item {
                  width: parent.width
                  height: input.height

                  TextField {
                    id: input
                    width: browseButton.visible ? parent.width - browseButton.width - Style.space(8) : parent.width
                    foreground: Color.menu.text
                    accent: Color.menu.selectedText
                    password: entry.modelData.masked === true
                    text: root.settingsValues[entry.modelData.key] || ""
                    placeholderText: SettingsForm.placeholder(entry.modelData, root.settingsPasswordStored)
                    onTextEdited: root.editSetting(entry.modelData.key, text)
                    onAccepted: root.saveSettings()
                    onActiveFocusChanged: if (activeFocus) root.settingsFocus = entry.modelData.key
                  }
                  Button {
                    id: browseButton
                    visible: SettingsForm.browses(entry.modelData.key)
                    anchors.right: parent.right
                    anchors.verticalCenter: input.verticalCenter
                    text: "Browse…"
                    bordered: true
                    foreground: Color.menu.text
                    accent: Color.menu.selectedText
                    fontFamily: Style.font.menuFamily
                    onClicked: root.browseFolder()
                  }
                }
                // The help line, or the field's problem in its place, in the accent color.
                Text {
                  width: parent.width
                  textFormat: Text.PlainText
                  text: entry.line.text
                  wrapMode: Text.Wrap
                  color: entry.line.problem ? Color.menu.selectedText : Color.menu.text
                  opacity: entry.line.problem || helpMouse.containsMouse ? 1 : root.secondaryOpacity
                  font.family: Style.font.menuFamily
                  font.pixelSize: Style.font.bodySmall
                  font.underline: entry.linked

                  MouseArea {
                    id: helpMouse
                    anchors.fill: parent
                    enabled: entry.linked
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.openLink(entry.modelData.key)
                  }
                }
              }
            }
          }

          Column {
            anchors.bottom: parent.bottom
            width: parent.width
            spacing: Style.space(6)

            Text {
              visible: text !== ""
              width: parent.width
              horizontalAlignment: Text.AlignHCenter
              wrapMode: Text.Wrap
              textFormat: Text.PlainText
              text: root.settingsStatus
              color: Color.menu.text
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.body
            }
            Text {
              width: parent.width
              horizontalAlignment: Text.AlignHCenter
              textFormat: Text.PlainText
              text: SettingsForm.footer(root.settingsFocus, root.settingsChanged, root.settingsSetup)
              color: Color.menu.text
              opacity: root.hintOpacity
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.bodySmall
              elide: Text.ElideRight
            }
          }
        }
      }
    }
  }
}
