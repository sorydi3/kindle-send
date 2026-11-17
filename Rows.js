// What the Picker shows and sends, from `kindle-send plan` lines. Pure functions, no QML.
// tr: the translator every text function takes (Catalog.js).
.pragma library
.import "Routes.js" as Routes
.import "Catalog.js" as Catalog

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

function routeLabel(route, tr) { return Routes.label(route, tr) }

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

// The footer's answer to "what does Enter send?". status: the marked count and,
// before Enter, which Routes can't take some of them (they still go and fail,
// spec §5). enter: the Enter hint, "" when Enter sends nothing.
function footer(books, marked, overrides, highlighted, tr) {
  const chosen = books.filter(function(b) { return marked && marked[b.path] === true })
  if (chosen.length === 0) {
    const sendsOne = highlighted && !highlighted.waiting
    return { status: "", enter: sendsOne ? tr.t("rows.sendThis") : "" }
  }
  const parts = [Catalog.count(tr, "rows.marked", chosen.length)]
  const routes = [Routes.EMAIL, Routes.USB]
  for (let i = 0; i < routes.length; i++) {
    const refused = chosen.filter(function(b) {
      return routeOf(b, overrides) === routes[i] && !routeTakes(b, routes[i])
    }).length
    if (refused > 0) parts.push(Catalog.count(tr, "rows.routeRefuses", refused, [routeLabel(routes[i], tr)]))
  }
  return { status: parts.join(tr.t("list.dot")), enter: Catalog.count(tr, "rows.sendCount", chosen.length) }
}

// A key hint: the key's name as it is, then what it does.
function hint(key, action) { return key + "  " + action }

// The gap between key hints.
const HINT_GAP = "      "

// Esc clears a search before it closes the Picker.
function escHint(filterText, tr) { return hint("Esc", tr.t(filterText ? "keys.clearSearch" : "keys.close")) }

// Every Book list footer ends with these: Ctrl+, opens Settings (spec §4, §9).
function closingHints(filterText, tr) { return hint("Ctrl+,", tr.t("keys.settings")) + HINT_GAP + escHint(filterText, tr) }

// The key hints for the highlighted row. enter: footer().enter.
function hints(current, enter, filterText, tr) {
  const keys = []
  if (current && current.waiting) keys.push(hint("Delete", tr.t("keys.cancelWaiting")))
  else if (current) keys.push(hint("Space", tr.t("keys.mark")), hint("Tab", tr.t("keys.route")))
  if (enter) keys.push(hint("Enter", enter))
  keys.push(closingHints(filterText, tr))
  return keys.join(HINT_GAP)
}

// What the Picker shows instead of the list, or null when it shows the list.
// state: {loading, failure: ""|"missing"|"failed"|"slow",
//         payloadCount, books, rows, waiting, filterText, bookFolders, program}.
// program: the bundled kindle-send's path, which the failure screens name
// (after a plain `omarchy plugin add` it isn't on PATH).
// A waiting line keeps the list up: it is where Delete cancels it.
// enter: what Enter does here: "settings" (opens them on `field`), "retry", "close" or "none".
// typing: whether typing still edits the search.
// settings: whether Ctrl+, opens Settings here (not without kindle-send).
// Setup needed has no screen: the Picker opens straight into Settings then (spec §4).
function screen(state, tr) {
  const settings = state.failure !== "missing"
  const program = String(state.program || "")
  function make(message, detail, enter, enterLabel, typing, field) {
    const keys = (enterLabel ? hint("Enter", enterLabel) + HINT_GAP : "")
      + (settings ? closingHints(state.filterText, tr) : escHint(state.filterText, tr))
    return { message: message, detail: detail, enter: enter, keys: keys, typing: typing === true,
             settings: settings, field: field || "" }
  }
  if (state.loading) {
    const what = state.payloadCount > 0 ? Catalog.count(tr, "rows.checkingFiles", state.payloadCount)
      : tr.t("rows.looking")
    return make(what, "", "none", "", true)
  }
  if (state.failure === "missing")
    return make(tr.t("rows.missing"), Catalog.say(tr, "rows.missingDetail", [program]), "close", "")
  if (state.failure === "failed")
    return make(tr.t("rows.failed"), Catalog.say(tr, "rows.failedDetail", [program]), "retry", tr.t("keys.retry"))
  if (state.failure === "slow")
    return make(tr.t("rows.slow"), Catalog.say(tr, "rows.slowDetail", [program]), "retry", tr.t("keys.retry"))
  if (state.waiting > 0) return null
  if (state.books === 0 && state.payloadCount > 0)
    return make(tr.t("rows.noneSendable"), "", "close", "")
  if (state.books === 0)
    return make(emptyMessage(state.bookFolders || [], tr), "", "settings", tr.t("keys.changeFolders"), false,
                "bookFolders")
  if (state.rows === 0)
    return make(Catalog.say(tr, "rows.noMatches", [state.filterText]), "", "none", "", true)
  return null
}

function size(bytes, tr) {
  if (bytes < 1000) return Catalog.say(tr, "size.bytes", [tr.num(bytes)])
  if (bytes < 1000000) return Catalog.say(tr, "size.kilobytes", [tr.num(Math.round(bytes / 1000))])
  return Catalog.say(tr, "size.megabytes", [tr.num(bytes / 1000000, 1)])
}

function sentAgo(iso, now, tr) {
  const t = Date.parse(iso)
  if (isNaN(t)) return ""
  const minutes = Math.floor((now - t) / 60000)
  if (minutes < 1) return tr.t("rows.sentJustNow")
  if (minutes < 60) return Catalog.count(tr, "rows.sentMinutesAgo", minutes)
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return Catalog.count(tr, "rows.sentHoursAgo", hours)
  const days = Math.floor(hours / 24)
  return days === 1 ? tr.t("rows.sentYesterday") : Catalog.count(tr, "rows.sentDaysAgo", days)
}

// "EPUB · 1.2 MB · sent 3 days ago", plus why the chosen Route can't take it.
// The format stays as it is: EPUB, PDF and so on are names, not words.
function details(book, route, now, tr) {
  const parts = [String(book.format).toUpperCase(), size(book.size, tr)]
  if (book.lastSent) parts.push(sentAgo(book.lastSent, now, tr))
  if (route === book.route && book.routeReason)
    parts.push(Catalog.message(tr, book.routeReasonCode, book.routeReasonValues, book.routeReason))
  else if (!routeTakes(book, route)) parts.push(Catalog.say(tr, "rows.routeCantTake", [routeLabel(route, tr)]))
  else if (route !== book.route) parts.push(Catalog.say(tr, "rows.switchedTo", [routeLabel(route, tr)]))
  return parts.filter(function(p) { return p }).join(tr.t("list.dot"))
}

function emptyMessage(folders, tr) {
  return folders.length > 0 ? Catalog.say(tr, "rows.noBooksIn", [folders.join(tr.t("list.separator"))])
    : tr.t("rows.noBooks")
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
