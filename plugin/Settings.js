// The Settings form's decisions (spec §9), rendered by the Picker. Pure functions, no QML.
// Values come from `kindle-send settings` and go to `kindle-send save`, which
// checks them; this module only maps its answer onto the form.
.pragma library

const FIELDS = [
  { key: "kindleAddress", label: "Kindle address", placeholder: "…@kindle.com",
    help: "Find it at amazon.com → Manage Your Content and Devices → Devices." },
  { key: "senderAddress", label: "Gmail address", placeholder: "…@gmail.com",
    help: "Amazon must list it as an approved sender, or it drops every Book." },
  // Masked, and never filled in: kindle-send settings only says whether one is stored (ADR 0001).
  { key: "appPassword", label: "Gmail app password", placeholder: "xxxx xxxx xxxx xxxx", masked: true,
    help: "Create one at myaccount.google.com/apppasswords. It needs 2-Step Verification." },
  { key: "bookFolders", label: "Book folders", placeholder: "~/Books, ~/Downloads",
    help: "The folders the Picker lists, separated by commas." }
]

function fields() { return FIELDS }

// The grey text in an empty field. A stored password stays stored until one is typed.
function placeholder(field, passwordStored) {
  if (field.masked && passwordStored) return "Stored. Type to replace it."
  return field.placeholder
}

// The page each field's help line links to (spec §9), keyed by field so a
// field added later (the app password) gets its link by its key alone.
const LINKS = {
  kindleAddress: "https://www.amazon.com/mycd",
  senderAddress: "https://www.amazon.com/hz/mycd/myx#/home/settings/pdoc",
  appPassword: "https://myaccount.google.com/apppasswords"
}

// The focused field's link, "" for a field without one (Book folders browse instead).
function link(key) { return Object.prototype.hasOwnProperty.call(LINKS, key) ? LINKS[key] : "" }

const KEY_COMMA = 0x2C
const KEY_B = 0x42
const KEY_O = 0x4F
const CONTROL = 0x04000000
const ALT = 0x08000000
const META = 0x10000000
const SHIFT = 0x02000000

// Ctrl+, in the Book list opens Settings; a plain comma still filters.
function opensSettings(key, modifiers) {
  return key === KEY_COMMA && (modifiers & (CONTROL | ALT | META | SHIFT)) === CONTROL
}

// Whether a field browses for a folder (Book folders do, instead of a link).
function browses(key) { return key === "bookFolders" }

// Ctrl+O in Settings opens the focused field's link.
function opensLink(key, modifiers) {
  return key === KEY_O && (modifiers & (CONTROL | ALT | META | SHIFT)) === CONTROL
}

// Ctrl+B in Settings browses for a Book folder.
function opensBrowse(key, modifiers) {
  return key === KEY_B && (modifiers & (CONTROL | ALT | META | SHIFT)) === CONTROL
}

// The command that opens a field's link, [] for a field without one.
function browserArgv(key) {
  const url = link(key)
  return url ? ["omarchy-launch-browser", url] : []
}

// The folder FolderDialog picked (a file URL) as the field writes it: `~/…`
// inside home, the full path elsewhere.
function chosenFolder(url, home) {
  let path = decodeURIComponent(String(url || "").replace(/^file:\/\//, ""))
  if (path.length > 1) path = path.replace(/\/+$/, "")
  const base = String(home || "").replace(/\/+$/, "")
  if (base === "") return path
  if (path === base) return "~"
  if (path.indexOf(base + "/") === 0) return "~" + path.slice(base.length)
  return path
}

// The Book folders field text with a picked folder appended. "" (Cancel) or
// a folder already listed leaves it as it was.
function withFolder(text, folder) {
  if (!folder) return String(text || "")
  const folders = String(text || "").split(",")
    .map(function(f) { return f.trim() }).filter(function(f) { return f !== "" })
  if (folders.indexOf(folder) < 0) folders.push(folder)
  return folders.join(", ")
}

// Form values (strings) from the line `kindle-send settings` printed.
function fromSettings(line) {
  const s = line || {}
  return {
    kindleAddress: String(s.kindleAddress || ""),
    senderAddress: String(s.senderAddress || ""),
    appPassword: "",
    bookFolders: Array.isArray(s.bookFolders) ? s.bookFolders.map(String).join(", ") : ""
  }
}

// What `kindle-send save` reads on stdin. Book folders split on commas; an
// empty list saves as the defaults there. The app password only when one was typed.
function toSave(values) {
  const out = {
    kindleAddress: String(values.kindleAddress || "").trim(),
    senderAddress: String(values.senderAddress || "").trim(),
    bookFolders: String(values.bookFolders || "").split(",")
      .map(function(f) { return f.trim() }).filter(function(f) { return f !== "" })
  }
  const password = String(values.appPassword || "")
  if (password.trim() !== "") out.appPassword = password
  return out
}

// The status line while save runs: it signs in to Gmail first when the Gmail
// address or the app password changed.
function savingStatus(values, saved) {
  const typed = String(values.appPassword || "").trim() !== ""
  const moved = String(values.senderAddress || "").trim() !== String(saved.senderAddress || "").trim()
  return typed || moved ? "Checking the app password with Gmail…" : "Saving…"
}

// Whether any field differs from what was loaded or last saved.
function changed(values, saved) {
  for (let i = 0; i < FIELDS.length; i++) {
    const key = FIELDS[i].key
    if (String(values[key] || "") !== String(saved[key] || "")) return true
  }
  return false
}

// save's problems as field key -> message (the first per field). A problem
// with no field is about the whole form and goes in the status line.
function byField(problems) {
  const shown = {}
  for (let i = 0; i < (problems || []).length; i++) {
    const p = problems[i]
    if (p.field && !(p.field in shown)) shown[p.field] = p.message
  }
  return shown
}

// The line under a field: its problem, in the accent color, or its help.
function helpLine(field, shown) {
  if (shown && shown[field.key]) return { text: shown[field.key], problem: true }
  return { text: field.help, problem: false }
}

// The field focus jumps to after a save: the first with a problem, "" if none.
function firstProblem(problems) {
  const shown = byField(problems)
  for (let i = 0; i < FIELDS.length; i++) if (FIELDS[i].key in shown) return FIELDS[i].key
  return ""
}

// Editing a field clears its problem at once; values are checked again on save only.
function edited(shown, key) {
  const next = Object.assign({}, shown)
  delete next[key]
  return next
}

function plural(n, one, many) { return n + " " + (n === 1 ? one : many) }

// The status line above the footer after a save. result: save's answer, or null before one.
function status(result) {
  if (!result) return ""
  const problems = result.problems || []
  const general = problems.filter(function(p) { return !p.field })
  if (general.length > 0) return general[0].message
  const fieldsWith = Object.keys(byField(problems)).length
  if (!result.saved) return plural(fieldsWith, "value needs", "values need") + " fixing"
  if (fieldsWith > 0) return "Saved. " + plural(fieldsWith, "value", "values") + " to check below."
  return "Saved."
}

// The keys that work on the focused field. Esc warns once something changed.
// Open link shows only on a field that has one, Browse only on Book folders.
function footer(focusedKey, isChanged) {
  const keys = ["Tab  Next field", "Enter  Save"]
  if (link(focusedKey)) keys.push("Ctrl+O  Open link")
  if (browses(focusedKey)) keys.push("Ctrl+B  Browse")
  keys.push(isChanged ? "Esc  Back (discard changes)" : "Esc  Back to Books")
  return keys.join("      ")
}

// --- Stepping aside -----------------------------------------------------------
// Opening a link or the folder chooser closes the Picker so the browser or the
// dialog shows. stepAside keeps the whole form (values, what was loaded,
// problems, status, focus) in memory only; reopened gives it back on the next
// open, or null for an ordinary open into the Book list.

function copy(value) {
  if (Array.isArray(value)) return value.map(copy)
  if (value && typeof value === "object") {
    const out = {}
    for (const k in value) out[k] = copy(value[k])
    return out
  }
  return value
}

function stepAside(form) { return { settings: copy(form) } }

function reopened(kept) { return kept && kept.settings ? copy(kept.settings) : null }
