// What the Picker shows and sends, from `kindle-send plan` lines. Pure functions, no QML.
.pragma library

const DEFAULT_FOLDERS = ["~/Books", "~/Downloads"]

// lines: parsed JSON lines of `kindle-send plan`, already newest first.
function fromPlan(lines) {
  let setupNeeded = false
  const books = []
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i]
    if (!l) continue
    if (l.setupNeeded) setupNeeded = true
    else if (l.path) books.push(l)
  }
  return { setupNeeded: setupNeeded, books: books }
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

function routeLabel(route) { return route === "usb" ? "USB" : "Email" }

function routeTakes(book, route) { return route === "usb" ? book.usbOk === true : book.emailOk === true }

// Marked Books in list order, or the highlighted one if none are marked.
// The "waiting for Kindle" line is not a Book and is never sent.
function toSend(books, marked, overrides, highlighted) {
  let chosen = books.filter(function(b) { return marked && marked[b.path] === true })
  if (chosen.length === 0 && highlighted && !highlighted.waiting) chosen = [highlighted]
  return chosen.map(function(b) { return { path: b.path, name: b.name, route: routeOf(b, overrides) } })
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
function details(book, route, now) {
  const parts = [String(book.format).toUpperCase(), size(book.size)]
  if (book.lastSent) parts.push(sentAgo(book.lastSent, now))
  if (route === book.route && book.routeReason) parts.push(book.routeReason)
  else if (!routeTakes(book, route)) parts.push(routeLabel(route) + " can't take this Book")
  return parts.filter(function(p) { return p }).join(" · ")
}

function foldersFromShellJson(text) {
  try {
    const cfg = JSON.parse(text || "{}")
    const list = Array.isArray(cfg.plugins) ? cfg.plugins : []
    for (let i = 0; i < list.length; i++) {
      const e = list[i]
      if (e && e.id === "sorydi3.kindle-send" && Array.isArray(e.bookFolders) && e.bookFolders.length > 0)
        return e.bookFolders.map(String)
    }
  } catch (e) {}
  return DEFAULT_FOLDERS
}

function emptyMessage(folders) {
  return "No Books found in " + folders.join(", ")
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
function planCommand(files) {
  return files.length > 0 ? ["kindle-send", "plan"].concat(files) : ["kindle-send", "plan", "--folders"]
}

// Every Book of a payload starts marked.
function allMarked(books) {
  const marked = {}
  for (let i = 0; i < books.length; i++) marked[books[i].path] = true
  return marked
}
