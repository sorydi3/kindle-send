// The plugin's text from its catalogs (spec §17, Translations). Pure, no QML.
// Every text function of the plugin's JS takes `tr`, a translator:
//   tr.t(key, fallback)      a catalog string (Commons.Translations.t)
//   tr.tn(key, count)        the plural form for count (Commons.Translations.tn)
//   tr.num(value, decimals)  a number as the language writes it (Commons.I18n.formatNumber)
//   tr.time(ms)              a time of day as the language writes it (Qt.locale(Commons.I18n.formatLocale))
// The Picker, the Service and the bar widget hand in Omarchy's; the tests a
// stand-in over i18n/en.json. Catalog strings carry %1, %2, … placeholders.
.pragma library

// "%2 of %1" with args [3, 1] is "1 of 3". A %n with no arg stays as it is;
// text inserted for one placeholder is never read for another.
function fill(text, args) {
  return String(text).replace(/%(\d)/g, function(all, n) {
    const i = Number(n) - 1
    return i >= 0 && i < args.length ? String(args[i]) : all
  })
}

// A catalog string with its placeholders filled.
function say(tr, key, args) { return fill(tr.t(key), args || []) }

// A plural entry for n, with n (formatted) as %1 and `more` as %2, %3, ….
function count(tr, key, n, more) { return fill(tr.tn(key, n), [tr.num(n)].concat(more || [])) }

// "a", "a and b", "a, b and c".
function list(tr, items) {
  if (items.length < 2) return items.length ? String(items[0]) : ""
  return fill(tr.t("list.and"), [items.slice(0, -1).join(tr.t("list.separator")), items[items.length - 1]])
}

// --- Notes: text kept in state as key and values, turned into text only in a
// binding, so a language switch re-renders it. A note is one of:
//   { key, args? }            a catalog string, args filled in (each may be a note)
//   { key, n, args? }         a plural entry for n (count)
//   { code, values, english } a kindle-send message (message)
//   { time: ms }              a time of day (tr.time)
//   "text"                    text as it is (already in the language, or a path)
//   null / ""                 no text
function text(tr, note) {
  if (note === null || note === undefined) return ""
  if (typeof note !== "object") return String(note)
  if ("time" in note) return tr.time(note.time)
  if ("code" in note) return message(tr, note.code, note.values, note.english)
  const args = (note.args || []).map(function(a) { return text(tr, a) })
  return typeof note.n === "number" ? count(tr, note.key, note.n, args) : say(tr, note.key, args)
}

// --- Key hints (the Picker's and the Settings form's footers) ---

// A key hint: the key's name as it is, then what it does.
function hint(key, action) { return key + "  " + action }

// The gap between key hints.
const HINT_GAP = "      "

// Key hints side by side.
function hints(list) { return list.join(HINT_GAP) }

// A Settings field's label, by its key (kindleAddress, …).
function fieldLabel(tr, key) { return tr.t("settings." + key + ".label", key) }

// The values each message code of kindle-send carries, in placeholder order
// (%1, %2, …). The codes and their values are pinned in tests/test_message_codes.py.
const ORDER = {
  too_big_for_email: ["mb"],
  format_not_emailable: ["format"],
  format_not_for_usb: ["format"],
  file_not_found: ["name"],
  not_set_up: ["fields"],
  gmail_unreachable: ["detail"],
  kindle_full: ["mb"],
  copy_failed: ["detail"],
  conversion_failed: ["detail"],
  route_format_not_emailable: ["format"],
  route_too_big_for_email: ["mb"],
  eject_failed: ["detail"],
  eject_step_failed: ["step"],
  book_folder_missing: ["folder"],
  book_folders_missing: ["folders"],
  settings_file_invalid: ["path"],
  settings_file_unwritable: ["path", "detail"],
  // The plugin's own codes, for a kindle-send that left no line to read.
  kindle_send_stopped: ["exit"],
  eject_stopped: ["exit"]
}

// How one value reads: sizes through the number formatter, field keys as
// their labels, lists joined; anything else (formats, names, paths, system
// and SMTP detail) as it is.
function value(tr, name, v) {
  if (name === "mb") return tr.num(v)
  if (name === "fields") return list(tr, (Array.isArray(v) ? v : []).map(function(k) { return fieldLabel(tr, String(k)) }))
  if (Array.isArray(v)) return list(tr, v.map(String))
  return v === undefined || v === null ? "" : String(v)
}

// A sentence kindle-send sent as { code, values } beside its English text:
// the catalog's text for the code, else that English text (a code this
// plugin doesn't know yet, or none at all).
function message(tr, code, values, english) {
  const fallback = english === undefined || english === null ? "" : String(english)
  if (!code) return fallback
  const text = tr.t("message." + code, "")
  if (!text) return fallback
  const v = values || {}
  return fill(text, (ORDER[code] || []).map(function(name) { return value(tr, name, v[name]) }))
}
