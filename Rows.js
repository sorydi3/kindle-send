// What the Picker shows and sends, from `kindle-send plan` lines. Pure functions, no QML.
.pragma library
.import "Routes.js" as Routes

// lines: parsed JSON lines of `kindle-send plan`, already newest first.
// Besides Books, plan says which Book folders it scans, so that default lives
// only in kindle-send. Routes come as ids; the plugin labels them (Routes.js).
function fromPlan(lines) {
  let setupNeeded = false
  let missing = []
  let bookFolders = []
  const books = []
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i]
    if (!l) continue
    if (l.setupNeeded) { setupNeeded = true; missing = Array.isArray(l.missing) ? l.missing.map(String) : [] }
    else if (Array.isArray(l.bookFolders)) bookFolders = l.bookFolders.map(String)
    else if (l.path) books.push(l)
  }
  return { setupNeeded: setupNeeded, missing: missing, books: books, bookFolders: bookFolders }
}

// Typing filters by file name only.
function filter(books, text) {
  const needle = String(text || "").toLowerCase()
  if (!needle) return books
  return books.filter(function(b) { return String(b.name).toLowerCase().indexOf(needle) !== -1 })
}

// The Route chosen for a Book: a Tab override, else plan's automatic one.
function routeOf(book, overrides) {
  return (overrides && overrides[book.path]) || book.route
}

// labels: optional Route labels by id (the Picker's); else Routes.LABELS.
function routeLabel(route, labels) { return Routes.label(route, labels) }

function switchRoute(route) { return Routes.other(route) }

// Tab: the overrides after switching the highlighted Book. On a marked Book,
// every marked Book moves to the Route the highlighted one switches to.
function switchRoutes(books, marked, overrides, highlighted) {
  const next = Object.assign({}, overrides)
  if (!highlighted || highlighted.waiting) return next
  const target = switchRoute(routeOf(highlighted, overrides))
  const together = marked && marked[highlighted.path] === true
  const moving = together ? books.filter(function(b) { return marked[b.path] === true }) : [highlighted]
  for (let i = 0; i < moving.length; i++) next[moving[i].path] = target
  return next
}

function routeTakes(book, route) { return route === Routes.USB ? book.usbOk === true : book.emailOk === true }

// Marked Books in list order, or the highlighted one if none are marked.
// The "waiting for Kindle" line is not a Book and is never sent.
function toSend(books, marked, overrides, highlighted) {
  let chosen = books.filter(function(b) { return marked && marked[b.path] === true })
  if (chosen.length === 0 && highlighted && !highlighted.waiting) chosen = [highlighted]
  return chosen.map(function(b) { return { path: b.path, name: b.name, route: routeOf(b, overrides) } })
}

function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s") }

// The footer's answer to "what does Enter send?". status: the marked count and,
// before Enter, which Routes can't take some of them (they still go and fail,
// spec §5). enter: the Enter hint, "" when Enter sends nothing.
function footer(books, marked, overrides, highlighted, labels) {
  const chosen = books.filter(function(b) { return marked && marked[b.path] === true })
  if (chosen.length === 0) {
    const sendsOne = highlighted && !highlighted.waiting
    return { status: "", enter: sendsOne ? "Send this Book" : "" }
  }
  const parts = [plural(chosen.length, "Book") + " marked"]
  const routes = [Routes.EMAIL, Routes.USB]
  for (let i = 0; i < routes.length; i++) {
    const refused = chosen.filter(function(b) {
      return routeOf(b, overrides) === routes[i] && !routeTakes(b, routes[i])
    }).length
    if (refused > 0) parts.push(routeLabel(routes[i], labels) + " can't take " + refused)
  }
  return { status: parts.join(" · "), enter: "Send " + plural(chosen.length, "Book") }
}

// Esc clears a search before it closes the Picker.
function escHint(filterText) { return filterText ? "Esc  Clear search" : "Esc  Close" }

// Every Book list footer ends with these: Ctrl+, opens Settings (spec §4, §9).
function closingHints(filterText) { return "Ctrl+,  Settings      " + escHint(filterText) }

// The key hints for the highlighted row. enter: footer().enter.
function hints(current, enter, filterText) {
  const keys = []
  if (current && current.waiting) keys.push("Delete  Cancel waiting")
  else if (current) keys.push("Space  Mark", "Tab  Route")
  if (enter) keys.push("Enter  " + enter)
  keys.push(closingHints(filterText))
  return keys.join("      ")
}

const PLAN_HINT = "kindle-send plan --folders"

// What the Picker shows instead of the list, or null when it shows the list.
// state: {loading, failure: ""|"missing"|"failed"|"slow",
//         payloadCount, books, rows, waiting, filterText, bookFolders}.
// A waiting line keeps the list up: it is where Delete cancels it.
// enter: what Enter does here: "settings" (opens them on `field`), "retry", "close" or "none".
// typing: whether typing still edits the search.
// settings: whether Ctrl+, opens Settings here (not without kindle-send).
// Setup needed has no screen: the Picker opens straight into Settings then (spec §4).
function screen(state) {
  const settings = state.failure !== "missing"
  function make(message, detail, enter, enterLabel, typing, field) {
    const keys = (enterLabel ? "Enter  " + enterLabel + "      " : "")
      + (settings ? closingHints(state.filterText) : escHint(state.filterText))
    return { message: message, detail: detail, enter: enter, keys: keys, typing: typing === true,
             settings: settings, field: field || "" }
  }
  if (state.loading) {
    const what = state.payloadCount > 0 ? "Checking " + plural(state.payloadCount, "file") + "…" : "Looking for Books…"
    return make(what, "", "none", "", true)
  }
  if (state.failure === "missing")
    return make("kindle-send isn't installed.", "Run scripts/install.sh from the kindle-send folder.", "close", "")
  if (state.failure === "failed")
    return make("Couldn't list your Books.", "To see the error, run " + PLAN_HINT + " in a terminal.",
                "retry", "Try again")
  if (state.failure === "slow")
    return make("Listing your Books took more than 10 seconds.",
                "To see what's slow, run " + PLAN_HINT + " in a terminal.", "retry", "Try again")
  if (state.waiting > 0) return null
  if (state.books === 0 && state.payloadCount > 0)
    return make("None of these files can be sent to a Kindle.", "", "close", "")
  if (state.books === 0)
    return make(emptyMessage(state.bookFolders || []), "", "settings", "Change Book folders", false, "bookFolders")
  if (state.rows === 0)
    return make("No matches for “" + state.filterText + "”", "", "none", "", true)
  return null
}

function size(bytes) {
  if (bytes < 1000) return bytes + " B"
  if (bytes < 1000000) return Math.round(bytes / 1000) + " KB"
  return (bytes / 1000000).toFixed(1) + " MB"
}

function sentAgo(iso, now) {
  const t = Date.parse(iso)
  if (isNaN(t)) return ""
  const minutes = Math.floor((now - t) / 60000)
  if (minutes < 1) return "sent just now"
  if (minutes < 60) return "sent " + minutes + " min ago"
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return "sent " + hours + " h ago"
  const days = Math.floor(hours / 24)
  return days === 1 ? "sent yesterday" : "sent " + days + " days ago"
}

// "EPUB · 1.2 MB · sent 3 days ago", plus why the chosen Route can't take it.
function details(book, route, now, labels) {
  const parts = [String(book.format).toUpperCase(), size(book.size)]
  if (book.lastSent) parts.push(sentAgo(book.lastSent, now))
  if (route === book.route && book.routeReason) parts.push(book.routeReason)
  else if (!routeTakes(book, route)) parts.push(routeLabel(route, labels) + " can't take this Book")
  else if (route !== book.route) parts.push("switched to " + routeLabel(route, labels))
  return parts.filter(function(p) { return p }).join(" · ")
}

function emptyMessage(folders) {
  return "No Books found in " + (folders.length > 0 ? folders.join(", ") : "your Book folders")
}

// --- Payload mode (spec §4): the Nautilus extension summons {"files": [...]} ---

// The files a summon asked for; [] for a bind's "{}" or anything unreadable.
function payloadFiles(payloadJson) {
  try {
    const p = JSON.parse(payloadJson || "{}")
    if (p && Array.isArray(p.files))
      return p.files.filter(function(f) { return typeof f === "string" && f !== "" })
  } catch (e) {}
  return []
}

// With files, plan just those; otherwise scan the Book folders.
// program: the bundled kindle-send's path (Program.js).
function planCommand(program, files) {
  return files.length > 0 ? [program, "plan"].concat(files) : [program, "plan", "--folders"]
}

// Every Book of a payload starts marked.
function allMarked(books) {
  const marked = {}
  for (let i = 0; i < books.length; i++) marked[books[i].path] = true
  return marked
}
