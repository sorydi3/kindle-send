// How the Service keeps to the Send limit (spec §11). Pure functions, no QML.
// `kindle-send limit` says when the next email may go; USB Books are not limited.
//
// A gap wait (seconds) is waited out inside the Send. Emails the hourly cap
// holds back leave their Send for the Service's held-email line, so the Send's
// USB Books, its eject and later Sends go on without them (spec §7, §11).
.pragma library
.import "Routes.js" as Routes

function capped(limit) {
  return limit.sentLastHour >= limit.maxEmailsPerHour
}

// What to do with Book `index` of a Send. `heldBusy`: emails are already held,
// so this one joins them (one email at a time, in order) without asking.
// Returns
//   { action: "send" }                   send it now
//   { action: "send", books }            send books[index] now: a USB Book brought forward
//   { action: "wait", ms }               a gap wait; ask again after ms
//   { action: "hold", books, held, notice }  the Send keeps `books` (its USB Books
//       from `index` on); `held` (its emails from `index` on) join the held line;
//       notice: the hold notice should go up.
function decide(books, index, limit, heldBusy) {
  if (books[index].route !== Routes.EMAIL) return { action: "send" }
  if (heldBusy) return hold(books, index, false)
  if (!limit || !(limit.canSendIn > 0)) return { action: "send" }
  if (capped(limit)) return hold(books, index, true)
  // USB isn't limited: bring the next USB Book of this Send forward instead of waiting.
  for (let j = index + 1; j < books.length; j++) {
    if (books[j].route !== Routes.EMAIL) {
      const order = books.slice(0, index).concat([books[j]], books.slice(index, j), books.slice(j + 1))
      return { action: "send", books: order }
    }
  }
  return { action: "wait", ms: limit.canSendIn * 1000 }
}

function hold(books, index, notice) {
  const rest = books.slice(index)
  return { action: "hold",
           books: books.slice(0, index).concat(rest.filter(function(b) { return b.route !== Routes.EMAIL })),
           held: rest.filter(function(b) { return b.route === Routes.EMAIL }),
           notice: notice }
}

// The next step of the held-email line. noticeUp: the hold notice is showing,
// so it stays (updated) through gap waits too.
// Returns { action: "send" } or { action: "wait", ms, notice }.
function heldStep(limit, noticeUp) {
  if (!limit || !(limit.canSendIn > 0)) return { action: "send" }
  return { action: "wait", ms: limit.canSendIn * 1000, notice: noticeUp || capped(limit) }
}

// The `kindle-send limit` state from its JSON lines, or null without one.
function parse(lines) {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i] && typeof lines[i].canSendIn === "number") return lines[i]
  }
  return null
}

// The hold notice (spec §10): critical, so it stays while Books are held.
// count: emails held; canSendIn: seconds until the next may go.
function holding(count, canSendIn) {
  const minutes = Math.max(1, Math.ceil(canSendIn / 60))
  return { headline: "Holding " + count + " Book" + (count === 1 ? "" : "s") + " to stay under Amazon's limit.",
           body: "Next in " + minutes + " min.", urgency: "critical" }
}
