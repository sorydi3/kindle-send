"""Runs the plugin's QML JavaScript libraries (the *.js at the repo root) under node.

QML-only lines are handled the way QML does: `.pragma library` is dropped and
`.import "Other.js" as Name` loads that file and binds it to `Name`.
Tests using this are skipped without node.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")

LOADER = r"""
const fs = require("fs"), vm = require("vm"), path = require("path")
function load(file) {
  const ctx = vm.createContext({})
  const src = fs.readFileSync(file, "utf8")
    .replace(/^\.pragma library.*$/m, "")
    .replace(/^\.import\s+"([^"]+)"\s+as\s+(\w+).*$/mg, function(_, dep, name) {
      ctx[name] = load(path.join(path.dirname(file), dep))
      return ""
    })
  vm.runInContext(src, ctx)
  return ctx
}
// The translators the plugin's text functions take ({t, tn, num}), standing in
// for Commons.Translations and Commons.I18n.formatNumber. EN reads i18n/en.json
// the way Translations does in English; LANG(entries) is a made-up language
// over it (its entries first, then English) that writes a decimal comma and,
// given zeroDigit (e.g. "٠"), that script's digits.
const catalogFile = path.join(path.dirname(process.argv[1]), "i18n", "en.json")
const english = fs.existsSync(catalogFile) ? JSON.parse(fs.readFileSync(catalogFile, "utf8")) : {}
function translator(entries, decimal, zeroDigit) {
  const strings = Object.assign({}, english, entries)
  return {
    t: function(key, fallback) {
      let v = strings[key]
      if (v && typeof v === "object") v = v.other
      return typeof v === "string" && v.length > 0 ? v : (fallback !== undefined ? fallback : key)
    },
    tn: function(key, count, fallback) {
      let v = strings[key]
      if (v && typeof v === "object") v = count === 1 && v.one ? v.one : v.other
      return typeof v === "string" && v.length > 0 ? v : (fallback !== undefined ? fallback : key)
    },
    num: function(value, decimals) {
      const n = Number(value)
      const text = decimals === undefined ? String(n) : n.toFixed(decimals)
      const zero = (zeroDigit || "0").charCodeAt(0)
      return text.replace(".", decimal)
        .replace(/[0-9]/g, function(d) { return String.fromCharCode(zero + d.charCodeAt(0) - 48) })
    }
  }
}
const ctx = load(process.argv[1])
ctx.EN = translator({}, ".")
ctx.LANG = function(entries, zeroDigit) { return translator(entries || {}, ",", zeroDigit) }
process.stdout.write(JSON.stringify(vm.runInContext(process.argv[2], ctx)))
"""


def evaluate(library, expr):
    """The JSON value of JS expression `expr`, evaluated inside <library> at the repo root."""
    out = subprocess.run([NODE, "-e", LOADER, str(PLUGIN / library), expr],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out) if out else None
