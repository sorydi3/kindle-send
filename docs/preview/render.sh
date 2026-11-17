#!/usr/bin/env bash
# Renders preview.png (spec §17) offscreen: the plugin's real Picker listing
# demo Books, beside Omarchy's own notification card showing the plugin's
# success text. Nothing appears on screen and nothing of the real home is used:
#
#   - HOME and the XDG dirs point at a throwaway folder holding demo Books and
#     demo Settings (reader@kindle.com, sender@gmail.com);
#   - Qt runs on the offscreen platform, under its own quickshell process (the
#     running shell is never touched);
#   - `secret-tool` is a stand-in that answers a demo password, so the real
#     keyring is never asked; nothing is sent, the Picker only runs `plan`.
#
# Only read: the active Omarchy theme (colours and wallpaper, copied into the
# throwaway home) and Omarchy's installed shell (qs.Commons, qs.Ui, the
# notifications plugin's Toast.qml).
#
#   docs/preview/render.sh [out.png]      default: preview.png at the repo root
#   OMARCHY_THEME_DIR=<dir>               another theme folder (colors.toml, shell.toml, backgrounds/)
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=$(realpath -m "${1:-$repo/preview.png}")
shell_dir=${OMARCHY_SHELL_DIR:-/usr/share/omarchy/shell}
theme_dir=${OMARCHY_THEME_DIR:-$HOME/.local/state/omarchy/current/theme}

work=$(mktemp -d)
cleanup() {
  if [ -n "${PREVIEW_KEEP:-}" ]; then echo "Kept $work" >&2; else rm -rf "$work"; fi
}
trap cleanup EXIT
home=$work/home
mkdir -p "$home/.config" "$home/.local/state" "$home/.local/share" "$work/bin" "$work/run"
chmod 700 "$work/run"

# The theme, read-only, where Omarchy's Color singleton looks for it.
theme=$home/.local/state/omarchy/current/theme
mkdir -p "$theme"
cp -L "$theme_dir/colors.toml" "$theme/" 2>/dev/null || true
cp -L "$theme_dir/shell.toml" "$theme/" 2>/dev/null || true
wallpaper=$(find -L "$theme_dir/backgrounds" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) 2>/dev/null | sort | head -n 1 || true)
if [ -n "$wallpaper" ]; then cp -L "$wallpaper" "$work/wallpaper"; fi

# Demo Books (empty files of plausible sizes) and demo Settings.
python3 - "$home" <<'PY'
import json, os, sys, time
home = sys.argv[1]
books = os.path.join(home, "Books")
os.makedirs(books)
now = time.time()
demo = [  # name, size in bytes, age in hours (newest first in the Picker)
    ("Pride and Prejudice.epub", 812_000, 1),
    ("Moby Dick.pdf", 3_400_000, 5),
    ("The Adventures of Sherlock Holmes.epub", 645_000, 26),
    ("Frankenstein.azw3", 1_150_000, 50),
    ("War and Peace.pdf", 78_000_000, 120),
    ("Little Women.epub", 930_000, 300),
]
for name, size, hours in demo:
    path = os.path.join(books, name)
    with open(path, "wb") as f:
        f.truncate(size)
    os.utime(path, (now - hours * 3600, now - hours * 3600))
settings = os.path.join(home, ".config", "kindle-send")
os.makedirs(settings)
with open(os.path.join(settings, "settings.json"), "w") as f:
    json.dump({"kindleAddress": "reader@kindle.com", "senderAddress": "sender@gmail.com",
               "bookFolders": ["~/Books"]}, f)
PY

# The keyring stand-in: a demo password for lookups, nothing else.
cat > "$work/bin/secret-tool" <<'SH'
#!/bin/sh
[ "$1" = lookup ] && printf 'demo-app-password'
exit 0
SH
chmod +x "$work/bin/secret-tool"

# The quickshell config: the scene, the plugin's own files, Omarchy's shell modules.
cfg=$work/config
mkdir -p "$cfg/plugin"
cp "$here/shell.qml" "$cfg/shell.qml"
cp "$repo"/*.qml "$repo"/*.js "$repo/manifest.json" "$cfg/plugin/"
cp -r "$repo/i18n" "$repo/bin" "$repo/assets" "$cfg/plugin/"
# A layer-shell window needs a Wayland compositor, which the offscreen platform
# doesn't have: the Picker's PanelWindow becomes a plain Item filling the scene
# (PreviewPanel.qml). Everything inside it, the card, is the Picker's own.
cp "$here/PreviewPanel.qml" "$cfg/plugin/"
python3 - "$cfg/plugin/Picker.qml" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path).read()
swaps = [
    (r"\n  PanelWindow \{\n", "\n  PreviewPanel {\n"),
    (r"\n    anchors \{ top: true; bottom: true; left: true; right: true \}\n", "\n"),
    (r"\n    WlrLayershell\.namespace: [^\n]*\n", "\n"),
    (r"\n    WlrLayershell\.layer: [^\n]*\n", "\n"),
    (r"\n    WlrLayershell\.keyboardFocus: [^\n]*\n", "\n"),
    (r"\n    exclusionMode: [^\n]*\n", "\n"),
]
for pattern, replacement in swaps:
    text, n = re.subn(pattern, replacement, text)
    if n != 1:
        sys.exit(f"Picker.qml changed shape: {pattern!r} matched {n} times")
open(path, "w").write(text)
PY
ln -s "$shell_dir/Commons" "$cfg/Commons"
ln -s "$shell_dir/Ui" "$cfg/Ui"
cp -r "$shell_dir/plugins/notifications" "$cfg/notifications"

# The offscreen screen the scene is drawn on.
cat > "$work/screens.json" <<'JSON'
{ "synchronousWindowSystemEvents": true,
  "screens": [{ "name": "preview", "x": 0, "y": 0, "width": 1200, "height": 750,
                "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 2 }] }
JSON

log=$work/quickshell.log
env -i \
  HOME="$home" XDG_CONFIG_HOME="$home/.config" XDG_STATE_HOME="$home/.local/state" \
  XDG_DATA_HOME="$home/.local/share" XDG_CACHE_HOME="$work/cache" XDG_RUNTIME_DIR="$work/run" \
  PATH="$work/bin:/usr/bin" LANG=C.UTF-8 \
  QT_QPA_PLATFORM="offscreen:configfile=$work/screens.json" \
  QML_XHR_ALLOW_FILE_READ=1 \
  PREVIEW_OUT="$out" PREVIEW_WALLPAPER="${wallpaper:+$work/wallpaper}" \
  quickshell --no-duplicate -p "$cfg/shell.qml" >"$log" 2>&1 &
pid=$!
for _ in $(seq 1 60); do
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.5
done
kill "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true

if grep -q "PREVIEW SAVED" "$log"; then
  echo "Wrote $out"
else
  cat "$log" >&2
  echo "No preview was written." >&2
  exit 1
fi
