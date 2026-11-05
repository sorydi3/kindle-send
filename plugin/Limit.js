// How the Service keeps to the Send limit (spec §11). Pure functions, no QML.
// `kindle-send limit` says when the next email may go; USB Books are not limited.
.pragma library

// What to do with Book `index` of a Send, given the `limit` state.
// Returns { action: "send" }, or { action: "wait", ms, held } where held means
// the hourly cap (not just the gap) is what keeps it back.
function decide(books, index, limit) {
  const book = books[index]
  if (book.route !== "email" || !limit || !(limit.canSendIn > 0)) return { action: "send" }
  // USB isn't limited: bring the next USB Book of this Send forward instead of waiting.
  for (let j = index + 1; j < books.length; j++) {
    if (books[j].route !== "email") {
      const order = books.slice(0, index).concat([books[j]], books.slice(index, j), books.slice(j + 1))
      return { action: "send", books: order }
    }
  }
  return { action: "wait", ms: limit.canSendIn * 1000,
           held: limit.sentLastHour >= limit.maxEmailsPerHour }
}

// The `kindle-send limit` state from its JSON lines, or null without one.
function parse(lines) {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i] && typeof lines[i].canSendIn === "number") return lines[i]
  }
  return null
}

// The Send limit hold notification (spec §10). Counts the emails still to go
// in this Send (from `index`) and in the Sends queued behind it.
function holding(books, index, queue, canSendIn) {
  const emails = function(list) { return list.filter(function(b) { return b.route === "email" }).length }
  let n = emails(books.slice(index))
  for (let i = 0; i < queue.length; i++) n += emails(queue[i].books)
  const minutes = Math.max(1, Math.ceil(canSendIn / 60))
  return { headline: "Holding " + n + " Book" + (n === 1 ? "" : "s") + " to stay under Amazon's limit.",
           body: "Next in " + minutes + " min." }
}
