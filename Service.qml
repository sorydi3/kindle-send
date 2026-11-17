// Runs Sends in the background (spec §2, §10). The Picker hands it Books and
// closes; this sends them one at a time with `kindle-send send` and keeps one
// notification per Send, updated in place, ending in a summary.
// Emails held by the Send limit leave their Send for a line of their own, so
// they never hold up USB Books, an eject or later Sends (spec §7, §11).
// It never sees the password: kindle-send reads the keyring itself.
// The decisions live in the pure JS libraries; this file only wires them up.
import QtQuick
import Quickshell
import Quickshell.Io
import "Feedback.js" as Feedback
import "Pending.js" as Pending
import "Limit.js" as Limit
import "Routes.js" as Routes
import "Program.js" as Program

Item {
  id: root

  // Injected by the shell.
  property var manifest: null

  // The kindle-send bundled in the plugin folder; every command runs it, never one from PATH (spec §17).
  readonly property string kindleSend: Program.path(Qt.resolvedUrl("bin/kindle-send"))

  // The plugin's own text (i18n/). Notification text is built when something
  // happens, in the language picked then.
  Translator {
    id: tr
  }

  // Sends waiting to start: [{ id, books: [{ path, name, route }] }]
  property var queue: []
  // The Send going out now, or null; results gathered so far.
  property var current: null
  property var results: []
  property int bookIndex: 0
  // The current Send's {"ejected": ...} line once it has ejected, else null.
  property var ejectResult: null
  property int nextSendId: 1
  readonly property bool busy: current !== null

  // A fresh notification key (Send ids and notice keys share one counter).
  function newKey() {
    const key = root.nextSendId
    root.nextSendId += 1
    return key
  }

  // books: [{ path, name, route }], route "email" or "usb".
  function enqueue(books) {
    const clean = []
    for (let i = 0; i < (books ? books.length : 0); i++) {
      const b = books[i]
      if (b && b.path) clean.push({ path: String(b.path), name: String(b.name || b.path), route: Routes.normalize(b.route) })
    }
    if (clean.length === 0) return
    root.queue = root.queue.concat([{ id: root.newKey(), books: clean }])
    if (!root.busy) root.startNext()
  }

  // --- Test send (spec §9) --------------------------------------------------
  // Settings' Ctrl+T: the bundled test Book goes by email like any Send. The
  // Picker's status line follows testSend: null before one, then
  // { state: "sending" }, then { state: "sent", at } or { state: "failed", at, code, values, reason, field }.
  property var testSend: null

  // sender: the saved Gmail address, named in the success summary.
  function sendTest(sender) {
    if (root.testSend && root.testSend.state === "sending") return
    root.testSend = { state: "sending" }
    root.queue = root.queue.concat([{ id: root.newKey(), books: [Feedback.testBook(sender)] }])
    if (!root.busy) root.startNext()
  }

  function testDone(book, result) {
    if (book.test !== true) return
    const t = { state: result.result === "sent" ? "sent" : "failed", at: Date.now() }
    if (t.state === "failed") {
      t.code = result.code || ""
      t.values = result.values || {}
      t.reason = result.reason || ""
      t.field = result.field || ""
    }
    root.testSend = t
  }

  function startNext() {
    if (root.queue.length === 0) { root.current = null; return }
    root.current = root.queue[0]
    root.queue = root.queue.slice(1)
    root.results = []
    root.waitingNow = []
    root.bookIndex = 0
    root.ejectResult = null
    root.advance()
  }

  // Next Book, the eject (as soon as no USB Book is left, spec §7), or the end.
  function advance() {
    const step = Feedback.nextStep(root.current.books, root.bookIndex, root.results, root.ejectResult !== null)
    if (step === "eject") root.startEject()
    else if (step === "book") root.sendBook()
    else root.finishSend()
  }

  // Send limit (spec §11): an email first asks `kindle-send limit`, unless
  // emails are already held, in which case it joins them. USB isn't limited.
  function sendBook() {
    if (root.current.books[root.bookIndex].route !== Routes.EMAIL) root.startBook()
    else if (root.held.length > 0) root.limitKnown(null)
    else limiter.ask()
  }

  function limitKnown(limit) {
    const send = root.current
    const d = Limit.decide(send.books, root.bookIndex, limit, root.held.length > 0)
    if (d.action === "wait") {
      limitTimer.interval = d.ms
      limitTimer.restart()
      return
    }
    if (d.action === "hold") {
      send.books = d.books
      root.holdEmails(d.held, d.notice, limit)
      root.advance()
      return
    }
    if (d.books) send.books = d.books
    root.startBook()
  }

  // Asks again once a gap wait is over; the history may have changed meanwhile.
  Timer { id: limitTimer; onTriggered: root.sendBook() }

  function startBook() {
    const send = root.current
    const p = Feedback.progressAt(send.books, root.bookIndex, tr)
    root.notify(send.id, p.headline, p.body, "normal", [])
    sender.runBook(send.books[root.bookIndex])
  }

  function bookDone(exitCode) {
    const book = root.current.books[root.bookIndex]
    const result = Feedback.resultFor(book, sender.lines, exitCode, sender.didStart)
    // A USB Book with no Kindle waits for it instead of failing (spec §7).
    if (Pending.isPending(book, result)) root.waitingNow = root.waitingNow.concat([book])
    else root.results = root.results.concat([result])
    root.testDone(book, result)
    root.bookIndex += 1
    root.advance()
  }

  function finishSend() {
    const send = root.current
    if (root.waitingNow.length > 0) root.holdPending(send.id, root.results.length)
    if (root.results.length > 0) {
      const s = Feedback.summary(root.results, root.ejectResult, tr)
      // A fully successful summary times out; any failure stays (critical) and,
      // when a Setting is the fix, a click opens Settings on it (spec §10, §13).
      // A sent test Book's click opens Settings (spec §9).
      root.notify(send.id, s.headline, s.body, s.urgency, Feedback.clickArgv(root.pluginId, s), s.timeout || 0)
    }
    root.startNext()
  }

  function showStage(line) {
    const send = root.current
    if (!send || !line || !line.stage) return
    const p = Feedback.stageAt(send.books, root.bookIndex, line.stage, tr)
    if (p) root.notify(send.id, p.headline, p.body, "normal", [])
  }

  // `kindle-send limit`, answered with the parsed state (null without one:
  // not installed or crashed, and then the email goes rather than stall).
  component LimitCheck: Process {
    id: check
    property var lines: []
    property bool didStart: false
    signal answered(var limit)
    function ask() { lines = []; didStart = false; running = true }
    command: [root.kindleSend, "limit"]
    stdout: SplitParser {
      onRead: function(line) {
        try { check.lines = check.lines.concat([JSON.parse(line)]) } catch (e) {}
      }
    }
    onStarted: didStart = true
    onRunningChanged: if (!running && !didStart) Qt.callLater(function() { check.answered(null) })
    onExited: Qt.callLater(function() { check.answered(Limit.parse(check.lines)) })
  }

  // One `kindle-send send` run; paths go as argv words, never through a shell.
  component BookRun: Process {
    id: bookRun
    property var lines: []
    property bool didStart: false
    signal stage(var line)
    signal done(int exitCode)
    function runBook(book) {
      lines = []
      didStart = false
      command = Feedback.sendArgv(root.kindleSend, book)
      running = true
    }
    stdout: SplitParser {
      onRead: function(line) {
        let v = null
        try { v = JSON.parse(line) } catch (e) { return }
        bookRun.lines = bookRun.lines.concat([v])
        bookRun.stage(v)
      }
    }
    onStarted: didStart = true
    // A program that cannot be found never starts and never exits.
    onRunningChanged: if (!running && !didStart) Qt.callLater(function() { bookRun.done(-1) })
    // Deferred, so the next Book starts after this run has fully stopped.
    onExited: function(exitCode) { Qt.callLater(function() { bookRun.done(exitCode) }) }
  }

  LimitCheck { id: limiter; onAnswered: function(limit) { root.limitKnown(limit) } }
  BookRun {
    id: sender
    onStage: function(line) { root.showStage(line) }
    onDone: function(exitCode) { root.bookDone(exitCode) }
  }

  // --- Emails held by the Send limit (spec §10, §11) ----------------------
  // In memory only, lost on a shell restart. They go one at a time, oldest
  // first, each after asking `kindle-send limit`. While the hourly cap holds
  // them, a critical notice of their own (never a Send's notification) says
  // how many and when; once the last has gone it turns into their summary.

  property var held: []
  property var heldResults: []
  // The notification key of the hold notice; 0 while it isn't up.
  property int holdKey: 0
  // When the next held email may go (ms since the epoch), for the notice.
  property real heldUntil: 0

  function holdEmails(books, notice, limit) {
    const idle = root.held.length === 0
    root.held = root.held.concat(books)
    if (limit && limit.canSendIn > 0) root.heldUntil = Date.now() + limit.canSendIn * 1000
    if (notice || root.holdKey > 0) root.showHold()
    if (idle) root.heldNext()
  }

  function showHold() {
    if (root.holdKey === 0) root.holdKey = root.newKey()
    const h = Limit.holding(root.held.length, Math.max(0, (root.heldUntil - Date.now()) / 1000), tr)
    root.notify(root.holdKey, h.headline, h.body, h.urgency, [])
  }

  function heldNext() {
    if (root.held.length > 0) { heldLimiter.ask(); return }
    if (root.heldResults.length > 0) {
      const s = Feedback.summary(root.heldResults, null, tr)
      root.notify(root.holdKey || root.newKey(), s.headline, s.body, s.urgency,
                  Feedback.clickArgv(root.pluginId, s), s.timeout || 0)
    }
    root.holdKey = 0
    root.heldResults = []
  }

  function heldLimitKnown(limit) {
    const d = Limit.heldStep(limit, root.holdKey > 0)
    if (d.action === "send") { heldSender.runBook(root.held[0]); return }
    root.heldUntil = Date.now() + d.ms
    if (d.notice) root.showHold()
    heldTimer.interval = d.ms
    heldTimer.restart()
  }

  // The email being sent stays first in `held` until it is done.
  function heldBookDone(exitCode) {
    const book = root.held[0]
    const result = Feedback.resultFor(book, heldSender.lines, exitCode, heldSender.didStart)
    root.heldResults = root.heldResults.concat([result])
    root.testDone(book, result)
    root.held = root.held.slice(1)
    if (root.holdKey > 0 && root.held.length > 0) root.showHold()
    root.heldNext()
  }

  Timer { id: heldTimer; onTriggered: root.heldNext() }
  LimitCheck { id: heldLimiter; onAnswered: function(limit) { root.heldLimitKnown(limit) } }
  BookRun { id: heldSender; onDone: function(exitCode) { root.heldBookDone(exitCode) } }

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
    if (key === 0) key = root.newKey()
    root.pendingKey = key
    const n = Pending.notice(root.pending, tr)
    root.notify(key, n.headline, n.body, n.urgency, root.pickerCommand)
  }

  // The Kindle is here: send every waiting Book. The new Send takes over the
  // waiting notice, so it turns into progress and then the summary.
  function releasePending() {
    if (root.pending.length === 0) return
    const id = root.pendingKey || root.newKey()
    root.queue = root.queue.concat([{ id: id, books: root.pending }])
    root.pending = []
    root.pendingKey = 0
    if (!root.busy) root.startNext()
  }

  function cancelPending() {
    if (root.pending.length === 0) return
    const c = Pending.cancelledNotice(root.pending, tr)
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
    command: [root.kindleSend, "kindle"]
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
    let result = { ejected: false, code: "eject_stopped", values: { exit: exitCode } }
    const lines = ejectOut.text.split("\n")
    for (let i = 0; i < lines.length; i++) {
      try {
        const v = JSON.parse(lines[i])
        if (v && v.ejected !== undefined) result = v
      } catch (e) {}
    }
    root.ejectResult = result
    root.advance()
  }

  Process {
    id: ejector
    property bool didStart: false
    property bool done: true
    command: [root.kindleSend, "eject"]
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

  // timeout (ms, optional): how long a normal notification stays; 0 = server default.
  function notify(sendId, headline, body, urgency, execArgv, timeout) {
    const item = { sendId: sendId, headline: headline, body: body, urgency: urgency, exec: execArgv, timeout: timeout || 0 }
    root.notifyQueue = root.notifyQueue.filter(function(q) { return q.sendId !== sendId }).concat([item])
    if (!notifier.running) root.postNext()
  }

  function postNext() {
    if (root.notifyQueue.length === 0) return
    const item = root.notifyQueue[0]
    root.notifyQueue = root.notifyQueue.slice(1)
    const id = root.notifyIds[item.sendId] || 0
    root.notifyFor = id > 0 ? 0 : item.sendId
    notifier.command = Feedback.notifyArgv(item, id, tr)
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
