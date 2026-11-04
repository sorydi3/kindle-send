// What the Send notification says (spec §10). Pure functions, no QML.
.pragma library

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

// A progress stage line ("copying", …) of the Book at `index`, or null if it changes nothing.
function stageAt(books, index, stage) {
  if (stage !== "copying") return null
  const body = books.length === 1 ? books[0].name : (index + 1) + " of " + books.length + ": " + books[index].name
  return { headline: "Copying to Kindle…", body: body }
}

// results: [{ name, result: "sent"|"copied"|"failed", reason?, fixBySetup? }]
// eject: the `kindle-send eject` line after the last USB Book, or null if there was none.
// Returns { headline, body, urgency, setup } where setup means a click should open setup.
function summary(results, eject) {
  const failed = results.filter(function(r) { return r.result === "failed" })
  const setup = failed.some(function(r) { return r.fixBySetup === true })
  const ejectLine = eject ? (eject.ejected === true ? EJECTED : EJECT_PLEASE) : ""
  // A Kindle still mounted needs the user, so that summary stays on screen too.
  const urgency = failed.length > 0 || (eject && eject.ejected !== true) ? "critical" : "normal"
  const done = function(r) { return r.result === "copied" ? COPIED : SENT }
  const anySent = results.some(function(r) { return r.result === "sent" })

  if (results.length === 1) {
    const only = results[0]
    if (only.result === "failed") return { headline: "Couldn't send " + only.name, body: only.reason, urgency: urgency, setup: setup }
    const tail = only.result === "copied" ? ejectLine : ARRIVES
    return { headline: only.name, body: done(only) + (tail ? " " + tail : ""), urgency: urgency, setup: setup }
  }

  const lines = results.map(function(r) {
    return r.name + ": " + (r.result === "failed" ? r.reason : done(r))
  })
  if (anySent) lines.push(ARRIVES)
  if (ejectLine) lines.push(ejectLine)
  const headline = failed.length === 0 ? "Sent " + plural(results.length, "Book")
    : failed.length === results.length ? "Couldn't send " + plural(results.length, "Book")
    : plural(failed.length, "Book") + " of " + results.length + " failed"
  return { headline: headline, body: lines.join("\n"), urgency: urgency, setup: setup }
}

// The result line of one `kindle-send send` run, or a failure when there was none.
function resultFor(book, lines, exitCode, started) {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i] && lines[i].result) {
      const r = { name: book.name, result: lines[i].result }
      if (lines[i].reason) r.reason = lines[i].reason
      if (lines[i].fixBySetup) r.fixBySetup = true
      return r
    }
  }
  const reason = !started ? "kindle-send is not installed. Run scripts/install.sh."
    : "kindle-send stopped without a result (exit " + exitCode + ")."
  return { name: book.name, result: "failed", reason: reason }
}
