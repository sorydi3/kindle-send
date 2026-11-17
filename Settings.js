// The Settings form's decisions (spec §9), rendered by the Picker. Pure functions, no QML.
// Values come from `kindle-send settings` and go to `kindle-send save`, which
// checks them; this module only maps its answer onto the form.
// tr: the translator every text function takes (Catalog.js).
.pragma library
.import "Catalog.js" as Catalog

// Each field's label, placeholder and help line are the catalog's
// settings.<key>.label, .placeholder and .help.
const FIELDS = [
  { key: "kindleAddress" },
  { key: "senderAddress" },
  // Masked, and never filled in: kindle-send settings only says whether one is stored (ADR 0001).
  { key: "appPassword", masked: true },
  { key: "bookFolders" }
]

function fields() { return FIELDS }

function label(field, tr) { return Catalog.fieldLabel(tr, field.key) }

function help(field, tr) { return tr.t("settings." + field.key + ".help") }

// The grey text in an empty field. A stored password stays stored until one is typed.
function placeholder(field, passwordStored, tr) {
  if (field.masked && passwordStored) return tr.t("settings.passwordStored")
  return tr.t("settings." + field.key + ".placeholder")
}

// The status line when `kindle-send settings` or `save` gave no answer.
// program: the bundled kindle-send's path, which isn't on PATH after a plain `omarchy plugin add`.
function readFailed(program, tr) { return Catalog.say(tr, "settings.readFailed", [program]) }

function saveFailed(program, tr) { return Catalog.say(tr, "settings.saveFailed", [program]) }

// Why `kindle-send settings` gave no values ({failed: true, code, values,
// reason}, e.g. an unreadable Settings file), for the status line; "" if it gave them.
function readProblem(line, tr) {
  if (!line || line.failed !== true) return ""
  return Catalog.message(tr, line.code, line.values, line.reason)
}

// The page each field's help line links to (spec §9), keyed by field key,
// apart from FIELDS. Book folders have none: they browse instead.
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

// Whether a key press is `wanted` with Ctrl and no other modifier.
function ctrlOnly(key, modifiers, wanted) {
  return key === wanted && (modifiers & (CONTROL | ALT | META | SHIFT)) === CONTROL
}

// Ctrl+, in the Book list opens Settings; a plain comma still filters.
function opensSettings(key, modifiers) { return ctrlOnly(key, modifiers, KEY_COMMA) }

// Whether a field browses for a folder (Book folders do, instead of a link).
function browses(key) { return key === "bookFolders" }

// Ctrl+O in Settings opens the focused field's link.
function opensLink(key, modifiers) { return ctrlOnly(key, modifiers, KEY_O) }

// Ctrl+B in Settings browses for a Book folder.
function opensBrowse(key, modifiers) { return ctrlOnly(key, modifiers, KEY_B) }

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

// The status line while save runs. Only a typed app password surely means a
// Gmail sign-in first; without one the form can't tell, so it just says saving.
function savingStatus(values, tr) {
  return tr.t(String(values.appPassword || "").trim() !== "" ? "settings.checkingPassword" : "settings.saving")
}

// Whether any field differs from what was loaded or last saved.
function changed(values, saved) {
  for (let i = 0; i < FIELDS.length; i++) {
    const key = FIELDS[i].key
    if (String(values[key] || "") !== String(saved[key] || "")) return true
  }
  return false
}

// A save problem's text: the catalog's for its code, else save's English message.
function problemText(p, tr) { return Catalog.message(tr, p.code, p.values, p.message) }

// The fields save found a problem with, in the order it named them.
function problemFields(problems) {
  const keys = []
  for (let i = 0; i < (problems || []).length; i++) {
    const p = problems[i]
    if (p.field && keys.indexOf(p.field) < 0) keys.push(p.field)
  }
  return keys
}

// save's problems as field key -> message (the first per field). A problem
// with no field is about the whole form and goes in the status line.
function byField(problems, tr) {
  const shown = {}
  for (let i = 0; i < (problems || []).length; i++) {
    const p = problems[i]
    if (p.field && !(p.field in shown)) shown[p.field] = problemText(p, tr)
  }
  return shown
}

// The line under a field: its problem, in the accent color, or its help.
function helpLine(field, shown, tr) {
  if (shown && shown[field.key]) return { text: shown[field.key], problem: true }
  return { text: help(field, tr), problem: false }
}

// The field focus jumps to after a save: the first with a problem, "" if none.
function firstProblem(problems) {
  const found = problemFields(problems)
  for (let i = 0; i < FIELDS.length; i++) if (found.indexOf(FIELDS[i].key) >= 0) return FIELDS[i].key
  return ""
}

// Editing a field clears its problem at once; values are checked again on save only.
function edited(shown, key) {
  const next = Object.assign({}, shown)
  delete next[key]
  return next
}

// The status line above the footer after a save. result: save's answer, or null before one.
function status(result, tr) {
  if (!result) return ""
  const problems = result.problems || []
  const general = problems.filter(function(p) { return !p.field })
  if (general.length > 0) return problemText(general[0], tr)
  const fieldsWith = problemFields(problems).length
  // A missing value is what setup is waiting for, so it's named before any typo.
  const stillNeeded = problems.filter(function(p) { return p.needed === true }).length
  if (!result.saved && stillNeeded > 0) return Catalog.count(tr, "settings.stillNeeded", stillNeeded)
  if (!result.saved) return Catalog.count(tr, "settings.fixing", fieldsWith)
  const saved = fieldsWith > 0 ? Catalog.count(tr, "settings.savedToCheck", fieldsWith) : tr.t("settings.saved")
  // The save that completed setup suggests the test send (spec §9).
  return result.firstSave === true ? Catalog.say(tr, "settings.savedSuggestTest", [saved]) : saved
}

// --- Test send (spec §9) --------------------------------------------------------
// Ctrl+T has the Service email the bundled test Book. It only checks what is
// saved, so it works only once everything is. testSend: the Service's state,
// null before any, else { state: "sending" | "sent" | "failed", at?, code?, values?, reason?, field? }.

const KEY_T = 0x54

function opensTestSend(key, modifiers) { return ctrlOnly(key, modifiers, KEY_T) }

// What Ctrl+T does: { send } to start one, else a status line saying why not.
function testKey(isSetup, isChanged, testSend, tr) {
  if (isSetup || isChanged) return { send: false, status: tr.t("settings.saveFirst") }
  if (testSend && testSend.state === "sending") return { send: false, status: tr.t("settings.sendingTest") }
  return { send: true, status: "" }
}

// The status line and field problems for the test send's state. A failure a
// Setting fixes shows next to that field, any other in the status line.
function testOutcome(testSend, tr) {
  const t = testSend || {}
  if (t.state === "sending") return { status: tr.t("settings.sendingTest"), problems: {} }
  if (t.state === "sent") return { status: Catalog.say(tr, "settings.testAccepted", [tr.time(t.at)]), problems: {} }
  if (t.state !== "failed") return { status: "", problems: {} }
  const reason = Catalog.message(tr, t.code, t.values, t.reason)
  if (t.field && FIELDS.some(function(f) { return f.key === t.field })) {
    const problems = {}
    problems[t.field] = reason
    return { status: tr.t("settings.testFailed"), problems: problems }
  }
  return { status: reason ? Catalog.say(tr, "settings.testFailedBecause", [reason]) : tr.t("settings.testFailed"),
           problems: {} }
}

// A key hint: the key's name as it is, then what it does.
function hint(key, action) { return key + "  " + action }

// The keys that work on the focused field. Esc warns once something changed;
// while setup is needed it closes the Picker instead (escCloses).
// Open link shows only on a field that has one, Browse only on Book folders.
function footer(focusedKey, isChanged, isSetup, tr) {
  const keys = [hint("Tab", tr.t("keys.nextField")), hint("Enter", tr.t("keys.save"))]
  if (link(focusedKey)) keys.push(hint("Ctrl+O", tr.t("keys.openLink")))
  if (browses(focusedKey)) keys.push(hint("Ctrl+B", tr.t("keys.browse")))
  if (isSetup) keys.push(hint("Esc", tr.t("keys.close")))
  else keys.push(hint("Esc", tr.t(isChanged ? "keys.discard" : "keys.backToBooks")))
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

// --- Opening on a field ----------------------------------------------------------
// A failure notification a Setting fixes summons the Picker with
// {"settings": <field key>, "problem": <the Send's reason>} (spec §10, §13).
// summoned gives { focus, problems } to open Settings on that field with its
// problem shown, or null for any other summon. A missing address reads as
// save would put it; the app password shows the Send's own reason (rejected or none stored).

// The fields a failed Send can name (kindle-send's result `field`).
const SEND_FIELDS = ["kindleAddress", "senderAddress", "appPassword"]

function summoned(payloadJson, tr) {
  let p = null
  try { p = JSON.parse(payloadJson || "{}") } catch (e) { return null }
  const key = p && typeof p.settings === "string" ? p.settings : ""
  if (SEND_FIELDS.indexOf(key) < 0) return null
  const reason = typeof p.problem === "string" ? p.problem : ""
  const problems = {}
  problems[key] = key === "appPassword" && reason ? reason : tr.t("message.value_needed")
  return { focus: key, problems: problems }
}

// The Omarchy menu's "Books to Kindle → Settings" summons with
// {"settings": ""}: open Settings on no field in particular (spec §14).
function opensFromMenu(payloadJson) {
  let p = null
  try { p = JSON.parse(payloadJson || "{}") } catch (e) { return false }
  return !!p && p.settings === ""
}

// Which way the Picker's open(payload) goes, given what stepAside kept (or null):
// { to: "settings", focus, problems } for the menu's entry (no field) or a
// failure notification (its field), ahead of anything kept; else
// { to: "returned", form } back to a form that stepped aside; else { to: "list" }.
function openIntent(payloadJson, kept, tr) {
  if (opensFromMenu(payloadJson)) return { to: "settings", focus: "", problems: {} }
  const onField = summoned(payloadJson, tr)
  if (onField) return { to: "settings", focus: onField.focus, problems: onField.problems }
  const back = reopened(kept)
  return back ? { to: "returned", form: back } : { to: "list" }
}

// --- Setup needed (spec §4, §9) -----------------------------------------------
// `missing`: the field keys `kindle-send settings` says setup still needs. One
// form serves setup and later changes; only its title, flags and Esc differ.

function setupNeeded(missing) { return Array.isArray(missing) && missing.length > 0 }

// Esc closes the Picker while setup is needed: there is no usable Book list yet.
function escCloses(missing) { return setupNeeded(missing) }

function title(missing, tr) { return tr.t(setupNeeded(missing) ? "settings.titleSetup" : "settings.title") }

// What setup still needs, from the line `kindle-send settings` printed.
function missing(line) {
  return line && Array.isArray(line.missing) ? line.missing.map(String) : []
}

// The flag beside a field's label (accent color): "· needed" for a missing
// value until the field is edited, "" otherwise.
function flag(key, missingKeys, values, saved, tr) {
  if (!Array.isArray(missingKeys) || missingKeys.indexOf(key) < 0) return ""
  return String(values[key] || "") === String(saved[key] || "") ? tr.t("settings.needed") : ""
}
