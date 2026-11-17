// Pending Sends (spec §7, §10): USB Books waiting for the Kindle to be plugged in.
// Held by the Service in memory only. Pure functions, no QML.
// tr: the translator every text function takes (Catalog.js).
.pragma library
.import "Routes.js" as Routes
.import "Catalog.js" as Catalog

function names(books, tr) {
  return books.map(function(b) { return b.name }).join(tr.t("list.separator"))
}

// A USB Book that failed only because no Kindle was found waits instead.
function isPending(book, result) {
  return book.route === Routes.USB && result.result === "failed" && result.code === "kindle_not_plugged_in"
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
function notice(books, tr) {
  if (books.length === 1)
    return { headline: Catalog.say(tr, "pending.waitingOne", [books[0].name]), body: tr.t("pending.plugIn"),
             urgency: "critical" }
  return { headline: Catalog.count(tr, "pending.waitingMany", books.length),
           body: names(books, tr) + "\n" + tr.t("pending.plugIn"), urgency: "critical" }
}

// Replaces the lasting notification after `Delete` in the Picker.
function cancelledNotice(books, tr) {
  return { headline: Catalog.count(tr, "pending.cancelled", books.length), body: "", urgency: "normal" }
}

// The notification key that carries the notice. pendingKey is the one already up (0: none).
// A Send whose every Book waits hands its own notification over; 0 means "take a new key".
function noticeKey(pendingKey, sendId, resultCount) {
  if (pendingKey > 0) return pendingKey
  return resultCount === 0 ? sendId : 0
}

// The Picker's rows with the "N Books waiting for Kindle" line on top while anything waits.
function withWaiting(rows, pending, tr) {
  if (!pending || pending.length === 0) return rows
  const line = { waiting: true, path: "", name: Catalog.count(tr, "pending.line", pending.length),
                 details: names(pending, tr) }
  return [line].concat(rows)
}
