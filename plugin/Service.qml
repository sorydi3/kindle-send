// Runs Sends in the background (spec §2, §10). The Picker hands it Books and
// closes; this sends them one at a time with `kindle-send send` and keeps one
// notification per Send, updated in place, ending in a summary.
// It never sees the password: kindle-send reads the keyring itself.
import QtQuick
import Quickshell
import Quickshell.Io
import "Feedback.js" as Feedback

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
    root.results = root.results.concat([Feedback.resultFor(book, sender.lines, exitCode, sender.didStart)])
    root.bookIndex += 1
    if (root.bookIndex < send.books.length) { root.sendBook(); return }
    const s = Feedback.summary(root.results)
    root.notify(send.id, s.headline, s.body, s.urgency, s.setup ? root.setupCommand : [])
    root.startNext()
  }

  Process {
    id: sender
    property var lines: []
    property bool didStart: false
    stdout: SplitParser {
      onRead: function(line) {
        try { sender.lines = sender.lines.concat([JSON.parse(line)]) } catch (e) {}
      }
    }
    onStarted: didStart = true
    // A program that cannot be found never starts and never exits.
    onRunningChanged: if (!running && !didStart && root.busy) root.bookDone(-1)
    // Deferred, so the next Book starts after this run has fully stopped.
    onExited: function(exitCode) { Qt.callLater(function() { root.bookDone(exitCode) }) }
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
