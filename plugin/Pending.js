// Pending Sends (spec §7, §10): USB Books waiting for the Kindle to be plugged in.
// Held by the Service in memory only. Pure functions, no QML.
.pragma library
.import "Routes.js" as Routes

const NO_KINDLE = "Kindle not plugged in"
const PLUG_IN = "Plug it in to send. Click to manage."

function plural(n, word) {
  return n + " " + word + (n === 1 ? "" : "s")
}

function names(books) {
  return books.map(function(b) { return b.name }).join(", ")
}

// A USB Book that failed only because no Kindle was found waits instead.
function isPending(book, result) {
  return book.route === Routes.USB && result.result === "failed"
    && String(result.reason || "").indexOf(NO_KINDLE) === 0
}

// Output of `kindle-send kindle`: true once a Kindle is mounted.
function kindleFound(text) {
  const lines = String(text || "").split("\n")
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const v = JSON.parse(lines[i])
      if (v && v.present !== undefined) return v.present === true
    } catch (e) {}
  }
  return false
}

// Books added to the waiting ones; a Book already waiting (same path) is kept once.
function add(pending, books) {
  const out = pending.slice()
  for (let i = 0; i < books.length; i++) {
    if (!out.some(function(p) { return p.path === books[i].path })) out.push(books[i])
  }
  return out
}

// The lasting notification while Books wait. Clicking it opens the Picker.
function notice(books) {
  if (books.length === 1)
    return { headline: "Waiting for Kindle: " + books[0].name, body: PLUG_IN, urgency: "critical" }
  return { headline: "Waiting for Kindle: " + plural(books.length, "Book"),
           body: names(books) + "\n" + PLUG_IN, urgency: "critical" }
}

// Replaces the lasting notification after `Delete` in the Picker.
function cancelledNotice(books) {
  return { headline: "Cancelled " + plural(books.length, "Book") + " waiting for Kindle", body: "", urgency: "normal" }
}

// The notification key that carries the notice. pendingKey is the one already up (0: none).
// A Send whose every Book waits hands its own notification over; 0 means "take a new key".
function noticeKey(pendingKey, sendId, resultCount) {
  if (pendingKey > 0) return pendingKey
  return resultCount === 0 ? sendId : 0
}

// The Picker's rows with the "N Books waiting for Kindle" line on top while anything waits.
function withWaiting(rows, pending) {
  if (!pending || pending.length === 0) return rows
  const line = { waiting: true, path: "", name: plural(pending.length, "Book") + " waiting for Kindle",
                 details: names(pending) + " · Delete  Cancel" }
  return [line].concat(rows)
}
