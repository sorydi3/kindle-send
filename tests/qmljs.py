"""Runs the plugin's QML JavaScript libraries (plugin/*.js) under node.

QML-only lines are handled the way QML does: `.pragma library` is dropped and
`.import "Other.js" as Name` loads that file and binds it to `Name`.
Tests using this are skipped without node.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent / "plugin"
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
const ctx = load(process.argv[1])
process.stdout.write(JSON.stringify(vm.runInContext(process.argv[2], ctx)))
"""


def evaluate(library, expr):
    """The JSON value of JS expression `expr`, evaluated inside plugin/<library>."""
    out = subprocess.run([NODE, "-e", LOADER, str(PLUGIN / library), expr],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out) if out else None
