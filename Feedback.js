// What the Send notification says (spec §10). Pure functions, no QML.
.pragma library
.import "Routes.js" as Routes

const SENT = "Sent to Amazon."
const ARRIVES = "Should appear on your Kindle within a few minutes."

function plural(n, word) {
  return n + " " + word + (n === 1 ? "" : "s")
}

// The first notification of a Send, before any Book is done.
function progress(books) {
  if (books.length === 1) return { headline: "Sending " + books[0].name + "…", body: "" }
  return { headline: "Sending " + plural(books.length, "Book") + "…", body: "" }
}

// While Book `index` (0-based) of a several-Book Send is going out.
function progressAt(books, index) {
  if (books.length === 1) return progress(books)
  return { headline: "Sending " + plural(books.length, "Book") + "…",
           body: (index + 1) + " of " + books.length + ": " + books[index].name }
}

const COPIED = "Copied to Kindle."
const EJECTED = "Kindle ejected, safe to unplug."
const EJECT_PLEASE = "Please eject the Kindle."

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
function stageAt(books, index, stage) {
  if (stage === "converting") {
    return { headline: "Converting " + books[index].name + "…",
             body: books.length === 1 ? "" : (index + 1) + " of " + books.length }
  }
  if (stage !== "copying") return null
  const body = books.length === 1 ? books[0].name : (index + 1) + " of " + books.length + ": " + books[index].name
  return { headline: "Copying to Kindle…", body: body }
}

// How long an all-fine summary stays up (ms). The server keeps a normal
// popup at least 8 s anyway; a critical one stays until dismissed (spec §10).
const DONE_TIMEOUT = 5000

// results: [{ name, result: "sent"|"copied"|"failed", reason?, fixBySetup?, field? }]
// eject: the `kindle-send eject` line after the last USB Book, or null if there was none.
// Returns { headline, body, urgency, fix, timeout? } where fix ({ field, reason },
// the first failure a Setting fixes, or null) is what a click opens Settings on,
// and timeout (ms) is set only when the summary should go away.
function summary(results, eject) {
  const s = summaryText(results, eject)
  if (s.urgency === "normal") s.timeout = DONE_TIMEOUT
  return s
}

function summaryText(results, eject) {
  const failed = results.filter(function(r) { return r.result === "failed" })
  // A failure naming a field is one a Setting fixes (its fixBySetup stays in the JSON for older readers).
  const fixable = failed.filter(function(r) { return !!r.field })
  const fix = fixable.length > 0 ? { field: fixable[0].field, reason: fixable[0].reason || "" } : null
  const ejectLine = eject ? (eject.ejected === true ? EJECTED : EJECT_PLEASE) : ""
  // A Kindle still mounted needs the user, so that summary stays on screen too.
  const urgency = failed.length > 0 || (eject && eject.ejected !== true) ? "critical" : "normal"
  const done = function(r) { return r.result === "copied" ? COPIED : SENT }
  const anySent = results.some(function(r) { return r.result === "sent" })

  if (results.length === 1) {
    const only = results[0]
    if (only.result === "failed") {
      return { headline: "Couldn't send " + only.name, body: only.reason, urgency: urgency, fix: fix }
    }
    // Amazon never confirms delivery, so the test send names what to check instead (spec §9).
    // Its click opens Settings (clickArgv); a failed one opens them only through fix.
    if (only.test === true) return { headline: only.name, body: testSent(only.sender), urgency: urgency, fix: fix, test: true }
    const tail = only.result === "copied" ? ejectLine : ARRIVES
    return { headline: only.name, body: done(only) + (tail ? " " + tail : ""), urgency: urgency, fix: fix }
  }

  const lines = results.map(function(r) {
    return r.name + ": " + (r.result === "failed" ? r.reason : done(r))
  })
  if (anySent) lines.push(ARRIVES)
  if (ejectLine) lines.push(ejectLine)
  const headline = failed.length === 0 ? "Sent " + plural(results.length, "Book")
    : failed.length === results.length ? "Couldn't send " + plural(results.length, "Book")
    : plural(failed.length, "Book") + " of " + results.length + " failed"
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
      if (lines[i].reason) r.reason = lines[i].reason
      if (lines[i].fixBySetup) r.fixBySetup = true
      if (lines[i].field) r.field = String(lines[i].field)
      return r
    }
  }
  const reason = !started ? "kindle-send is not installed. Run scripts/install.sh."
    : "kindle-send stopped without a result (exit " + exitCode + ")."
  return { name: book.name, result: "failed", reason: reason }
}

// --- The test send (spec §9, §10) ---------------------------------------------
// Settings' Ctrl+T sends the bundled test EPUB as "Kindle Send Test" like any
// Send: `kindle-send send --route email --test`, which finds the file itself.

const TEST_NAME = "Kindle Send Test"

// sender: the saved Gmail address, which the success summary names.
function testBook(sender) {
  return { test: true, path: "", name: TEST_NAME, route: Routes.EMAIL, sender: String(sender || "") }
}

// The `kindle-send send` argv for one Book; paths go as argv words, never through a shell.
function sendArgv(book) {
  return ["kindle-send", "send", "--route", book.route, book.test === true ? "--test" : book.path]
}

function testSent(sender) {
  return SENT + " Not on your Kindle in a few minutes? Check that " + (sender || "your Gmail address") +
    " is on Amazon's approved list and the Kindle address is right."
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
// and has to come last.
function notifyArgv(item, replaceId) {
  let argv = ["omarchy-notification-send", "--app-name", "Books to Kindle", "-g", "\u{F02D}", "-u", item.urgency]
  if (item.timeout > 0) argv = argv.concat(["-t", String(item.timeout)])
  argv = replaceId > 0 ? argv.concat(["-r", String(replaceId)]) : argv.concat(["-p"])
  argv = argv.concat([item.headline, item.body || ""])
  if (item.exec && item.exec.length) argv = argv.concat(["--exec"]).concat(item.exec)
  return argv
}
