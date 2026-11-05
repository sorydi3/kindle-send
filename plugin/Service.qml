// Runs Sends in the background (spec §2, §10). The Picker hands it Books and
// closes; this sends them one at a time with `kindle-send send` and keeps one
// notification per Send, updated in place, ending in a summary.
// It never sees the password: kindle-send reads the keyring itself.
import QtQuick
import Quickshell
import Quickshell.Io
import "Feedback.js" as Feedback
import "Pending.js" as Pending

Item {
  id: root

  // Injected by the shell.
  property var manifest: null

  // Sends waiting to start: [{ id, books: [{ path, name, route }] }]
  property var queue: []
  // The Send going out now, or null; results gathered so far.
  property var current: null
  property var results: []
  property int bookIndex: 0
  property int nextSendId: 1
  readonly property bool busy: current !== null

  readonly property var setupCommand: ["omarchy-launch-floating-terminal-with-presentation", "kindle-send", "setup"]

  // books: [{ path, name, route }], route "email" or "usb".
  function enqueue(books) {
    const clean = []
    for (let i = 0; i < (books ? books.length : 0); i++) {
      const b = books[i]
      if (b && b.path) clean.push({ path: String(b.path), name: String(b.name || b.path), route: b.route === "usb" ? "usb" : "email" })
    }
    if (clean.length === 0) return
    root.queue = root.queue.concat([{ id: root.nextSendId, books: clean }])
    root.nextSendId += 1
    if (!root.busy) root.startNext()
  }

  function startNext() {
    if (root.queue.length === 0) { root.current = null; return }
    root.current = root.queue[0]
    root.queue = root.queue.slice(1)
    root.results = []
    root.waitingNow = []
    root.bookIndex = 0
    root.sendBook()
  }

  function sendBook() {
    const send = root.current
    const book = send.books[root.bookIndex]
    const p = Feedback.progressAt(send.books, root.bookIndex)
    root.notify(send.id, p.headline, p.body, "normal", [])
    sender.lines = []
    sender.didStart = false
    // Paths go as argv words, never through a shell.
    sender.command = ["kindle-send", "send", "--route", book.route, book.path]
    sender.running = true
  }

  function bookDone(exitCode) {
    const send = root.current
    const book = send.books[root.bookIndex]
    const result = Feedback.resultFor(book, sender.lines, exitCode, sender.didStart)
    // A USB Book with no Kindle waits for it instead of failing (spec §7).
    if (Pending.isPending(book, result)) root.waitingNow = root.waitingNow.concat([book])
    else root.results = root.results.concat([result])
    root.bookIndex += 1
    if (root.bookIndex < send.books.length) { root.sendBook(); return }
    // One eject after the last USB Book of the Send (spec §7).
    if (Feedback.needsEject(root.results)) { root.startEject(); return }
    root.finishSend(null)
  }

  function finishSend(eject) {
    const send = root.current
    if (root.waitingNow.length > 0) root.holdPending(send.id, root.results.length)
    if (root.results.length > 0) {
      const s = Feedback.summary(root.results, eject)
      root.notify(send.id, s.headline, s.body, s.urgency, s.setup ? root.setupCommand : [])
    }
    root.startNext()
  }

  function showStage(line) {
    const send = root.current
    if (!send || !line || !line.stage) return
    const p = Feedback.stageAt(send.books, root.bookIndex, line.stage)
    if (p) root.notify(send.id, p.headline, p.body, "normal", [])
  }

  Process {
    id: sender
    property var lines: []
    property bool didStart: false
    stdout: SplitParser {
      onRead: function(line) {
        let v = null
        try { v = JSON.parse(line) } catch (e) { return }
        sender.lines = sender.lines.concat([v])
        root.showStage(v)
      }
    }
    onStarted: didStart = true
    // A program that cannot be found never starts and never exits.
    onRunningChanged: if (!running && !didStart && root.busy) root.bookDone(-1)
    // Deferred, so the next Book starts after this run has fully stopped.
    onExited: function(exitCode) { Qt.callLater(function() { root.bookDone(exitCode) }) }
  }

  // --- Pending Sends (spec §7, §10) ---------------------------------------
  // USB Books that found no Kindle wait here, in memory only, while
  // `kindle-send kindle` is polled every 3 s. Once a Kindle shows up they all
  // go out as one Send (so one eject). One lasting notification covers them;
  // clicking it opens the Picker, where Delete on the waiting line cancels.

  // Books waiting for the Kindle: [{ path, name, route }]. The Picker reads it.
  property var pending: []
  // USB Books of the current Send that found no Kindle.
  property var waitingNow: []
  // The notification key (a Send id) showing the waiting notice; 0 when none.
  property int pendingKey: 0
  readonly property string pluginId: manifest && manifest.id ? String(manifest.id) : "sorydi3.kindle-send"
  readonly property var pickerCommand: ["omarchy-shell", "shell", "summon", root.pluginId]

  function holdPending(sendId, resultCount) {
    root.pending = Pending.add(root.pending, root.waitingNow)
    root.waitingNow = []
    let key = Pending.noticeKey(root.pendingKey, sendId, resultCount)
    if (key === 0) { key = root.nextSendId; root.nextSendId += 1 }
    root.pendingKey = key
    const n = Pending.notice(root.pending)
    root.notify(key, n.headline, n.body, n.urgency, root.pickerCommand)
  }

  // The Kindle is here: send every waiting Book. The new Send takes over the
  // waiting notice, so it turns into progress and then the summary.
  function releasePending() {
    if (root.pending.length === 0) return
    let id = root.pendingKey
    if (id === 0) { id = root.nextSendId; root.nextSendId += 1 }
    root.queue = root.queue.concat([{ id: id, books: root.pending }])
    root.pending = []
    root.pendingKey = 0
    if (!root.busy) root.startNext()
  }

  function cancelPending() {
    if (root.pending.length === 0) return
    const c = Pending.cancelledNotice(root.pending)
    if (root.pendingKey > 0) root.notify(root.pendingKey, c.headline, c.body, c.urgency, [])
    root.pending = []
    root.pendingKey = 0
  }

  Timer {
    id: kindlePoll
    interval: 3000
    repeat: true
    running: root.pending.length > 0
    onTriggered: if (!kindleCheck.running) kindleCheck.running = true
  }

  Process {
    id: kindleCheck
    command: ["kindle-send", "kindle"]
    stdout: StdioCollector { id: kindleOut }
    onExited: Qt.callLater(function() { if (Pending.kindleFound(kindleOut.text)) root.releasePending() })
  }

  // --- Eject ----------------------------------------------------------------

  function startEject() {
    ejector.done = false
    ejector.didStart = false
    ejector.running = true
  }

  // The last {"ejected": ...} line, or a failure if there was none.
  function ejectDone(exitCode) {
    if (ejector.done) return
    ejector.done = true
    let result = { ejected: false, reason: "kindle-send eject stopped without a result (exit " + exitCode + ")." }
    const lines = ejectOut.text.split("\n")
    for (let i = 0; i < lines.length; i++) {
      try {
        const v = JSON.parse(lines[i])
        if (v && v.ejected !== undefined) result = v
      } catch (e) {}
    }
    root.finishSend(result)
  }

  Process {
    id: ejector
    property bool didStart: false
    property bool done: true
    command: ["kindle-send", "eject"]
    stdout: StdioCollector { id: ejectOut }
    onStarted: didStart = true
    onRunningChanged: if (!running && !didStart && !done) root.ejectDone(-1)
    onExited: function(exitCode) { Qt.callLater(function() { root.ejectDone(exitCode) }) }
  }

  // --- Notifications ------------------------------------------------------
  // One notification per Send: the first post prints its id (-p), later ones
  // replace it (-r). Posts run one at a time; a queued post for the same Send
  // is superseded by a newer one, since only the latest text matters.

  property var notifyIds: ({})
  property var notifyQueue: []
  property int notifyFor: 0

  function notify(sendId, headline, body, urgency, execArgv) {
    const item = { sendId: sendId, headline: headline, body: body, urgency: urgency, exec: execArgv }
    root.notifyQueue = root.notifyQueue.filter(function(q) { return q.sendId !== sendId }).concat([item])
    if (!notifier.running) root.postNext()
  }

  function postNext() {
    if (root.notifyQueue.length === 0) return
    const item = root.notifyQueue[0]
    root.notifyQueue = root.notifyQueue.slice(1)
    let argv = ["omarchy-notification-send", "--app-name", "Send to Kindle", "-g", "\u{F02D}", "-u", item.urgency]
    const id = root.notifyIds[item.sendId] || 0
    argv = id > 0 ? argv.concat(["-r", String(id)]) : argv.concat(["-p"])
    argv = argv.concat([item.headline, item.body || ""])
    if (item.exec && item.exec.length) argv = argv.concat(["--exec"]).concat(item.exec)
    root.notifyFor = id > 0 ? 0 : item.sendId
    notifier.command = argv
    notifier.running = true
  }

  Process {
    id: notifier
    property bool didStart: false
    stdout: StdioCollector { id: notifyOut }
    onStarted: didStart = true
    onRunningChanged: {
      if (running) return
      if (!didStart) { root.notifyFor = 0; Qt.callLater(root.postNext) }
      didStart = false
    }
    onExited: function(exitCode) {
      if (exitCode === 0 && root.notifyFor > 0) {
        const ids = Object.assign({}, root.notifyIds)
        ids[root.notifyFor] = parseInt(notifyOut.text.trim(), 10) || 0
        root.notifyIds = ids
      }
      root.notifyFor = 0
      Qt.callLater(root.postNext)
    }
  }
}
