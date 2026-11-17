#!/usr/bin/env bash
# Renders preview.png (spec §17) offscreen: the plugin's real Picker listing
# demo Books, beside Omarchy's own notification card showing the plugin's
# success text. It runs in harness.sh's throwaway world: demo Books and
# Settings, a stand-in keyring, the offscreen platform; nothing is sent.
#
#   docs/preview/render.sh [out.png]      default: preview.png at the repo root
#   OMARCHY_THEME_DIR=<dir>               another theme folder (colors.toml, shell.toml, backgrounds/)
set -euo pipefail

source "$(dirname "$0")/harness.sh"
out=$(realpath -m "${1:-$repo/preview.png}")

if run_scene "$here/shell.qml" 30 PREVIEW_OUT="$out"; then
  echo "Wrote $out"
else
  echo "No preview was written." >&2
  exit 1
fi
