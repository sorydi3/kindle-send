// The Settings form's decisions (spec §9), rendered by the Picker. Pure functions, no QML.
// Values come from `kindle-send settings` and go to `kindle-send save`, which
// checks them; this module only maps its answer onto the form.
.pragma library

const FIELDS = [
  { key: "kindleAddress", label: "Kindle address", placeholder: "…@kindle.com",
    help: "Find it at amazon.com → Manage Your Content and Devices → Devices." },
  { key: "senderAddress", label: "Gmail address", placeholder: "…@gmail.com",
    help: "Amazon must list it as an approved sender, or it drops every Book." },
  { key: "bookFolders", label: "Book folders", placeholder: "~/Books, ~/Downloads",
    help: "The folders the Picker lists, separated by commas." }
]

function fields() { return FIELDS }

const KEY_COMMA = 0x2C
const CONTROL = 0x04000000
const ALT = 0x08000000
const META = 0x10000000
const SHIFT = 0x02000000

// Ctrl+, in the Book list opens Settings; a plain comma still filters.
function opensSettings(key, modifiers) {
  return key === KEY_COMMA && (modifiers & (CONTROL | ALT | META | SHIFT)) === CONTROL
}

// Form values (strings) from the line `kindle-send settings` printed.
function fromSettings(line) {
  const s = line || {}
  return {
    kindleAddress: String(s.kindleAddress || ""),
    senderAddress: String(s.senderAddress || ""),
    bookFolders: Array.isArray(s.bookFolders) ? s.bookFolders.map(String).join(", ") : ""
  }
}

// What `kindle-send save` reads on stdin. Book folders split on commas; an
// empty list saves as the defaults there.
function toSave(values) {
  return {
    kindleAddress: String(values.kindleAddress || "").trim(),
    senderAddress: String(values.senderAddress || "").trim(),
    bookFolders: String(values.bookFolders || "").split(",")
      .map(function(f) { return f.trim() }).filter(function(f) { return f !== "" })
  }
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
// focusedKey is unused until fields gain keys of their own (Open link, Browse).
function footer(focusedKey, isChanged) {
  const keys = ["Tab  Next field", "Enter  Save"]
  keys.push(isChanged ? "Esc  Back (discard changes)" : "Esc  Back to Books")
  return keys.join("      ")
}
