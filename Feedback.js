// What the Send notification says (spec §10). Pure functions, no QML.
// tr: the translator every text function takes (Catalog.js).
.pragma library
.import "Routes.js" as Routes
.import "Catalog.js" as Catalog

// "2 of 5: Atlas.pdf", or just "2 of 5" without a name.
function position(tr, index, total, name) {
  const at = Catalog.say(tr, "feedback.position", [tr.num(index + 1), tr.num(total)])
  return name === undefined ? at : Catalog.say(tr, "feedback.positionNamed", [at, name])
}

// The first notification of a Send, before any Book is done.
function progress(books, tr) {
  if (books.length === 1) return { headline: Catalog.say(tr, "feedback.sendingOne", [books[0].name]), body: "" }
  return { headline: Catalog.count(tr, "feedback.sendingMany", books.length), body: "" }
}

// While Book `index` (0-based) of a several-Book Send is going out.
function progressAt(books, index, tr) {
  if (books.length === 1) return progress(books, tr)
  return { headline: Catalog.count(tr, "feedback.sendingMany", books.length),
           body: position(tr, index, books.length, books[index].name) }
}

// Eject once after the last USB Book of a Send, if any Book was copied.
function needsEject(results) {
  return results.some(function(r) { return r.result === "copied" })
}

// What a Send does once Book `index - 1` is done: "eject" as soon as no USB
// Book is left and something was copied (its emails needn't keep the Kindle
// mounted), else "book" for the next one, or "finish".
function nextStep(books, index, results, ejected) {
  const usbLeft = books.slice(index).some(function(b) { return b.route === Routes.USB })
  if (!usbLeft && !ejected && needsEject(results)) return "eject"
  return index < books.length ? "book" : "finish"
}

// A progress stage line ("converting", "copying") of the Book at `index`, or null if it changes nothing.
function stageAt(books, index, stage, tr) {
  if (stage === "converting") {
    return { headline: Catalog.say(tr, "feedback.converting", [books[index].name]),
             body: books.length === 1 ? "" : position(tr, index, books.length) }
  }
  if (stage !== "copying") return null
  const body = books.length === 1 ? books[0].name : position(tr, index, books.length, books[index].name)
  return { headline: tr.t("feedback.copying"), body: body }
}

// How long an all-fine summary stays up (ms). The server keeps a normal
// popup at least 8 s anyway; a critical one stays until dismissed (spec §10).
const DONE_TIMEOUT = 5000

// A failed result's reason as the catalog says it (its code), else kindle-send's English.
function reason(r, tr) { return Catalog.message(tr, r.code, r.values, r.reason) }

// results: [{ name, result: "sent"|"copied"|"failed", code?, values?, reason?, fixBySetup?, field? }]
// eject: the `kindle-send eject` line after the last USB Book, or null if there was none.
// Returns { headline, body, urgency, fix, timeout? } where fix ({ field, reason },
// the first failure a Setting fixes, or null) is what a click opens Settings on,
// and timeout (ms) is set only when the summary should go away.
function summary(results, eject, tr) {
  const s = summaryText(results, eject, tr)
  if (s.urgency === "normal") s.timeout = DONE_TIMEOUT
  return s
}

function summaryText(results, eject, tr) {
  const failed = results.filter(function(r) { return r.result === "failed" })
  // A failure naming a field is one a Setting fixes (its fixBySetup stays in the JSON for older readers).
  const fixable = failed.filter(function(r) { return !!r.field })
  const fix = fixable.length > 0 ? { field: fixable[0].field, reason: reason(fixable[0], tr) } : null
  const ejectLine = eject ? tr.t(eject.ejected === true ? "feedback.ejected" : "feedback.ejectPlease") : ""
  // A Kindle still mounted needs the user, so that summary stays on screen too.
  const urgency = failed.length > 0 || (eject && eject.ejected !== true) ? "critical" : "normal"
  const done = function(r) { return tr.t(r.result === "copied" ? "feedback.copied" : "feedback.sentToAmazon") }
  const anySent = results.some(function(r) { return r.result === "sent" })

  if (results.length === 1) {
    const only = results[0]
    if (only.result === "failed") {
      return { headline: Catalog.say(tr, "feedback.failedOne", [only.name]), body: reason(only, tr),
               urgency: urgency, fix: fix }
    }
    // Amazon never confirms delivery, so the test send names what to check instead (spec §9).
    // Its click opens Settings (clickArgv); a failed one opens them only through fix.
    if (only.test === true)
      return { headline: only.name, body: testSent(only.sender, tr), urgency: urgency, fix: fix, test: true }
    const tail = only.result === "copied" ? ejectLine : tr.t("feedback.arrives")
    return { headline: only.name, body: done(only) + (tail ? " " + tail : ""), urgency: urgency, fix: fix }
  }

  const lines = results.map(function(r) {
    return Catalog.say(tr, "feedback.bookLine", [r.name, r.result === "failed" ? reason(r, tr) : done(r)])
  })
  if (anySent) lines.push(tr.t("feedback.arrives"))
  if (ejectLine) lines.push(ejectLine)
  const headline = failed.length === 0 ? Catalog.count(tr, "feedback.sent", results.length)
    : failed.length === results.length ? Catalog.count(tr, "feedback.failedAll", results.length)
    : Catalog.count(tr, "feedback.failedSome", failed.length, [tr.num(results.length)])
  return { headline: headline, body: lines.join("\n"), urgency: urgency, fix: fix }
}

// The result line of one `kindle-send send` run, or a failure when there was none.
// A test Book's result keeps the Gmail address for its summary.
function resultFor(book, lines, exitCode, started) {
  const r = resultLine(book, lines, exitCode, started)
  if (book.test === true) { r.test = true; r.sender = String(book.sender || "") }
  return r
}

function resultLine(book, lines, exitCode, started) {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i] && lines[i].result) {
      const r = { name: book.name, result: lines[i].result }
      if (lines[i].code) r.code = String(lines[i].code)
      if (lines[i].values && typeof lines[i].values === "object") r.values = lines[i].values
      if (lines[i].reason) r.reason = lines[i].reason
      if (lines[i].fixBySetup) r.fixBySetup = true
      if (lines[i].field) r.field = String(lines[i].field)
      return r
    }
  }
  // The plugin's own codes (i18n/en.json): no kindle-send line to take English from.
  // The bundled kindle-send didn't start: the plugin folder is broken (spec §17).
  if (!started) return { name: book.name, result: "failed", code: "kindle_send_missing", values: {} }
  return { name: book.name, result: "failed", code: "kindle_send_stopped", values: { exit: exitCode } }
}

// --- The test send (spec §9, §10) ---------------------------------------------
// Settings' Ctrl+T sends the bundled test EPUB as "Kindle Send Test" like any
// Send: `kindle-send send --route email --test`, which finds the file itself.

// The test Book's name, as its title shows on the Kindle: a name, so it stays as it is.
const TEST_NAME = "Kindle Send Test"

// sender: the saved Gmail address, which the success summary names.
function testBook(sender) {
  return { test: true, path: "", name: TEST_NAME, route: Routes.EMAIL, sender: String(sender || "") }
}

// The `kindle-send send` argv for one Book; paths go as argv words, never through a shell.
// program: the bundled kindle-send's path (Program.js).
function sendArgv(program, book) {
  return [program, "send", "--route", book.route, book.test === true ? "--test" : book.path]
}

function testSent(sender, tr) {
  return sender ? Catalog.say(tr, "feedback.testSent", [sender]) : tr.t("feedback.testSentNoSender")
}

// What a click on a failure a Setting fixes runs: the Picker summoned straight
// into Settings on that field, with the reason to show there (spec §10, §13).
// [] when there is no such failure.
function settingsArgv(pluginId, fix) {
  if (!fix || !fix.field) return []
  return ["omarchy-shell", "shell", "summon", pluginId,
          JSON.stringify({ settings: fix.field, problem: fix.reason || "" })]
}

// What a click on a summary runs: Settings on the field at fault, else Settings
// themselves for a sent test Book, else nothing (spec §9, §13).
function clickArgv(pluginId, summary) {
  const onField = settingsArgv(pluginId, summary.fix)
  if (onField.length > 0 || summary.test !== true) return onField
  return ["omarchy-shell", "shell", "summon", pluginId, JSON.stringify({ settings: "" })]
}

// The omarchy-notification-send argv for one post. replaceId 0 posts a new
// notification and prints its id (-p); otherwise it replaces that one (-r).
// item: { headline, body, urgency, timeout?, exec? }; exec (argv) runs on click
// and has to come last. The app name is the plugin's name (the catalog's app.name).
function notifyArgv(item, replaceId, tr) {
  let argv = ["omarchy-notification-send", "--app-name", tr.t("app.name"), "-g", "\u{F02D}", "-u", item.urgency]
  if (item.timeout > 0) argv = argv.concat(["-t", String(item.timeout)])
  argv = replaceId > 0 ? argv.concat(["-r", String(replaceId)]) : argv.concat(["-p"])
  argv = argv.concat([item.headline, item.body || ""])
  if (item.exec && item.exec.length) argv = argv.concat(["--exec"]).concat(item.exec)
  return argv
}
