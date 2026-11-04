#!/usr/bin/env bash
# Install Send to Kindle into the current user's home. Needs no root.
#
#   ./scripts/install.sh
#
# Copies the kindle-send command and the omarchy-shell plugin, links the
# plugin into Omarchy's plugins folder, rescans plugins and enables it.
# Safe to run again: it updates in place.
set -euo pipefail

case "${1:-}" in
  -h | --help)
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  "") ;;
  *)
    echo "Unknown option: $1 (try --help)" >&2
    exit 2
    ;;
esac

repo="$(cd "$(dirname "$0")/.." && pwd)"

plugin_id=sorydi3.kindle-send
bin_dir="$HOME/.local/bin"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/kindle-send"
plugin_copy="$data_dir/omarchy-plugin"
plugin_link="$config_dir/omarchy/plugins/$plugin_id"

echo "==> Installing the command"
mkdir -p "$bin_dir"
install -m 755 "$repo/bin/kindle-send" "$bin_dir/kindle-send"
echo "    $bin_dir/kindle-send"
if [[ -d $repo/assets ]]; then
  mkdir -p "$data_dir"
  rm -rf "$data_dir/assets"
  cp -r "$repo/assets" "$data_dir/assets"
  echo "    $data_dir/assets"
fi

echo "==> Omarchy plugin"
plugin_listed() {
  local tries
  for tries in 1 2 3 4 5 6 7 8 9 10; do
    omarchy plugin list --json 2>/dev/null | grep -qF "\"$plugin_id\"" && return 0
    sleep 0.2
  done
  return 1
}

copy_plugin() {
  mkdir -p "$data_dir"
  rm -rf "$plugin_copy"
  cp -r "$repo/plugin" "$plugin_copy"
}

if ! command -v omarchy >/dev/null; then
  echo "    Not Omarchy (no 'omarchy' command); plugin not added."
  exit 0
fi

if [[ -L $plugin_link && $(readlink "$plugin_link") == "$plugin_copy" ]]; then
  copy_plugin
  echo "    Updated $plugin_copy."
elif [[ -e $plugin_link || -L $plugin_link ]]; then
  # A development link or clone is never replaced.
  echo "    $plugin_link is not the installer's; left alone."
else
  copy_plugin
  mkdir -p "$(dirname "$plugin_link")"
  ln -s "$plugin_copy" "$plugin_link"
  echo "    Linked $plugin_link."
fi

omarchy-shell -q shell rescanPlugins || true
# It has no bar widget, so nothing else enables it.
if plugin_listed && omarchy plugin enable "$plugin_id" >/dev/null; then
  echo "    Enabled. Open the picker with: omarchy-shell shell toggle $plugin_id"
else
  echo "    Warning: Omarchy's shell did not pick the plugin up; once it is" >&2
  echo "    running, run: omarchy plugin enable $plugin_id" >&2
fi

case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *) echo "Note: $bin_dir is not on your PATH in this shell." ;;
esac
