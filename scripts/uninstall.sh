#!/usr/bin/env bash
# Remove what scripts/install.sh installed. Needs no root.
#
#   ./scripts/uninstall.sh [--purge]
#
# Removes the command, the plugin and its link, the Nautilus item, and the
# keybinding and menu blocks between the installer's markers. Keeps your
# settings in shell.json, the app password in the keyring and the Send
# history, so a later install picks up where you left off.
#
#   --purge  also delete the settings, the app password and the Send history
set -euo pipefail

purge=no
for argument in "$@"; do
  case "$argument" in
    --purge) purge=yes ;;
    -h | --help)
      sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $argument (try --help)" >&2
      exit 2
      ;;
  esac
done

repo="$(cd "$(dirname "$0")/.." && pwd)"

plugin_id=sorydi3.kindle-send
bin_dir="$HOME/.local/bin"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}"
share_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/kindle-send"
data_dir="$share_dir/kindle-send"
program="$data_dir/bin/kindle-send"
plugin_copy="$data_dir/omarchy-plugin"
plugin_link="$config_dir/omarchy/plugins/$plugin_id"
nautilus_ext="$share_dir/nautilus-python/extensions/kindle-send.py"
bindings="$config_dir/hypr/bindings.lua"
menu="$config_dir/omarchy/extensions/omarchy-menu.jsonc"
shell_json="${KINDLE_SEND_SHELL_JSON:-$config_dir/omarchy/shell.json}"
bind_start="-- >>> kindle-send keybinding (added by scripts/install.sh) >>>"
bind_end="-- <<< kindle-send <<<"
menu_block=("$repo/scripts/menu_block.py")

# Remove the bindings block and the one blank line the installer put before it.
remove_bindings_block() {
  awk -v start="$bind_start" -v end="$bind_end" '
    inside      { if ($0 == end) inside = 0; next }
    $0 == start { inside = 1; for (i = 1; i < blanks; i++) print ""; blanks = 0; next }
    $0 == ""    { blanks++; next }
                { for (i = 0; i < blanks; i++) print ""; blanks = 0; print }
    END         { for (i = 0; i < blanks; i++) print "" }
  ' "$bindings" >"$bindings.kindle-send-tmp"
  cat "$bindings.kindle-send-tmp" >"$bindings"
  rm -f "$bindings.kindle-send-tmp"
}

# Before the command, which the plugin runs.
echo "==> Omarchy plugin"
if [[ -L $plugin_link && $(readlink "$plugin_link") == "$plugin_copy" ]]; then
  # Not `omarchy plugin remove`: it disables the plugin, and disabling drops
  # the plugin's entry, settings included, from shell.json.
  rm -f "$plugin_link"
  if command -v omarchy-shell >/dev/null; then
    omarchy-shell -q shell rescanPlugins || true
  fi
  echo "    Removed $plugin_link."
elif [[ -e $plugin_link || -L $plugin_link ]]; then
  echo "    $plugin_link is not the installer's; left alone."
else
  echo "    Not installed."
fi
rm -rf "$plugin_copy"

echo "==> Removing files"
if [[ -L $bin_dir/kindle-send && $(readlink "$bin_dir/kindle-send") == "$program" ]] ||
  { [[ -f $bin_dir/kindle-send && ! -L $bin_dir/kindle-send ]] &&
    grep -qF "PLUGIN_ID = \"$plugin_id\"" "$bin_dir/kindle-send"; }; then
  rm -f "$bin_dir/kindle-send"
  echo "    $bin_dir/kindle-send"
elif [[ -e $bin_dir/kindle-send || -L $bin_dir/kindle-send ]]; then
  echo "    $bin_dir/kindle-send is not the installer's; left alone."
fi
rm -rf "$data_dir/bin" "$data_dir/assets"
rmdir "$data_dir" 2>/dev/null || true
if [[ -f $nautilus_ext ]]; then
  rm -f "$nautilus_ext"
  echo "    $nautilus_ext"
  if command -v nautilus >/dev/null; then
    nautilus -q 2>/dev/null || true
  fi
fi

echo "==> Keybinding"
if [[ -f $bindings ]] && grep -qF -- "$bind_start" "$bindings"; then
  remove_bindings_block
  echo "    Removed from $bindings."
else
  echo "    None was added by the installer."
fi

echo "==> Omarchy menu"
if [[ -f $menu ]] && grep -qF -- "// >>> kindle-send menu" "$menu"; then
  before="$menu.kindle-send-uninstall"
  cp -p "$menu" "$before"
  python3 -I "${menu_block[@]}" remove "$menu"
  if python3 -I "${menu_block[@]}" check "$menu"; then
    rm -f "$before"
    echo "    Removed from $menu."
  else
    mv "$before" "$menu"
    echo "    Warning: removing the entries broke $menu, so it was put back." >&2
    echo "    Delete the lines between the kindle-send markers by hand." >&2
  fi
else
  echo "    None were added by the installer."
fi

echo "==> Settings, app password and Send history"
if [[ $purge == yes ]]; then
  if [[ -f $shell_json ]]; then
    python3 -I - "$shell_json" "$plugin_id" <<'EOF' || true
import json, os, shutil, sys
path, plugin = sys.argv[1], sys.argv[2]
try:
    config = json.load(open(path, encoding="utf-8"))
except ValueError:
    sys.exit(f"    {path} is not valid JSON; settings left in it.")
plugins = config.get("plugins")
if isinstance(plugins, list):
    config["plugins"] = [p for p in plugins if not (isinstance(p, dict) and p.get("id") == plugin)]
    tmp = path + ".kindle-send-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    shutil.copymode(path, tmp)
    os.replace(tmp, path)
EOF
  fi
  secret-tool clear service kindle-send 2>/dev/null || true
  rm -rf "$state_dir"
  echo "    Deleted."
else
  echo "    Kept: settings in $shell_json, the app password in the keyring,"
  echo "    and $state_dir. Run with --purge to delete them too."
fi

echo "Send to Kindle is uninstalled."
