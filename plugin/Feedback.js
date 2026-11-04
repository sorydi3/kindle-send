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

// results: [{ name, result: "sent"|"copied"|"failed", reason?, fixBySetup? }]
// Returns { headline, body, urgency, setup } where setup means a click should open setup.
function summary(results) {
  const failed = results.filter(function(r) { return r.result === "failed" })
  const setup = failed.some(function(r) { return r.fixBySetup === true })
  const urgency = failed.length > 0 ? "critical" : "normal"

  if (results.length === 1) {
    const only = results[0]
    if (only.result === "failed") return { headline: "Couldn't send " + only.name, body: only.reason, urgency: urgency, setup: setup }
    return { headline: only.name, body: SENT + " " + ARRIVES, urgency: urgency, setup: setup }
  }

  const lines = results.map(function(r) {
    return r.name + ": " + (r.result === "failed" ? r.reason : SENT)
  })
  if (failed.length < results.length) lines.push(ARRIVES)
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
