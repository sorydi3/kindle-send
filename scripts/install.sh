#!/usr/bin/env bash
# Install Books to Kindle into the current user's home. Needs no root.
#
#   ./scripts/install.sh [--yes | --no-config]
#
#   --yes        make the config edits (keybinding, Omarchy menu) without asking
#   --no-config  do not make them and do not ask
#
# With neither option it asks before each edit, and makes none if it cannot
# ask (no terminal). Each edited file is backed up first, and the lines it
# adds sit between ">>> kindle-send" / "<<< kindle-send" markers.
# Safe to run again: it updates in place and adds nothing twice.
set -euo pipefail

config_edits=ask
for argument in "$@"; do
  case "$argument" in
    --yes | -y) config_edits=yes ;;
    --no-config) config_edits=no ;;
    -h | --help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
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
data_dir="$share_dir/kindle-send"
program="$data_dir/bin/kindle-send"
plugin_copy="$data_dir/omarchy-plugin"
plugin_link="$config_dir/omarchy/plugins/$plugin_id"
nautilus_dir="$share_dir/nautilus-python/extensions"
nautilus_python="${KINDLE_SEND_NAUTILUS_PYTHON:-/usr/lib/nautilus/extensions-4/libnautilus-python.so}"
bindings="$config_dir/hypr/bindings.lua"
menu="$config_dir/omarchy/extensions/omarchy-menu.jsonc"
bind_start="-- >>> kindle-send keybinding (added by scripts/install.sh) >>>"
bind_end="-- <<< kindle-send <<<"
menu_block=("$repo/scripts/menu_block.py")

echo "==> Checking dependencies"
missing=()
for tool in python3 secret-tool udisksctl; do
  command -v "$tool" >/dev/null || missing+=("$tool")
done
[[ -e $nautilus_python ]] || missing+=(nautilus-python)
if ((${#missing[@]})); then
  declare -A package=([python3]=python [secret-tool]=libsecret [udisksctl]=udisks2 [nautilus-python]=nautilus-python)
  for tool in "${missing[@]}"; do
    echo "Missing: $tool. Install it with: sudo pacman -S ${package[$tool]}" >&2
  done
  echo "Nothing was installed. Run this script again once they are there." >&2
  exit 1
fi
echo "    python3, nautilus-python, secret-tool, udisksctl: found"
command -v ebook-convert >/dev/null || echo "    Optional: sudo pacman -S calibre to send EPUB over USB"

echo "==> Installing files"
# The program lives beside its assets, so it finds assets/test.epub through
# the link in ~/.local/bin.
mkdir -p "$data_dir/bin" "$bin_dir"
install -m 755 "$repo/bin/kindle-send" "$program"
rm -rf "$data_dir/assets"
cp -r "$repo/assets" "$data_dir/assets"
rm -f "$bin_dir/kindle-send"
ln -s "$program" "$bin_dir/kindle-send"
echo "    $bin_dir/kindle-send -> $program"
echo "    $data_dir/assets"
mkdir -p "$nautilus_dir"
install -m 644 "$repo/nautilus/kindle-send.py" "$nautilus_dir/kindle-send.py"
echo "    $nautilus_dir/kindle-send.py"

# ask QUESTION: the answer to one config edit, from the options or the terminal.
ask() {
  local answer
  case $config_edits in
    yes) return 0 ;;
    no) return 1 ;;
  esac
  if [[ -t 0 ]]; then
    read -r -p "    $1 [y/N] " answer || return 1
    [[ ${answer,,} == y || ${answer,,} == yes ]]
  else
    return 1
  fi
}

not_added() {
  if [[ $config_edits == ask && ! -t 0 ]]; then
    echo "    Not added: no terminal to ask in. Run again in a terminal, or with --yes."
  else
    echo "    Not added."
  fi
}

echo "==> Keybinding SUPER + SHIFT + K"
if [[ ! -f $bindings ]] || ! grep -q 'o\.bind' "$bindings"; then
  echo "    No Omarchy bindings file at $bindings; nothing added."
elif grep -qF -- "$bind_start" "$bindings"; then
  echo "    Already in $bindings."
elif ask "Add SUPER + SHIFT + K (open the picker) to $bindings?"; then
  cp -p "$bindings" "$bindings.before-kindle-send"
  {
    echo
    echo "$bind_start"
    echo "o.bind(\"SUPER + SHIFT + K\", \"Books to Kindle\", \"omarchy-shell shell toggle $plugin_id\")"
    echo "$bind_end"
  } >>"$bindings"
  echo "    Added. Your previous file is kept as $bindings.before-kindle-send."
else
  not_added
fi

echo "==> Omarchy menu: Books to Kindle, and Books to Kindle > Settings"
edit=add question="Add them to $menu?" done="Added to"
if [[ -f $menu ]] && grep -qF -- "// >>> kindle-send menu" "$menu"; then
  # An older install's block (its "Setup" entry ran the terminal wizard) is swapped in place.
  edit=update question="Replace the older Books to Kindle entries in $menu?" done="Updated in"
fi
if [[ $edit == update ]] && python3 -I "${menu_block[@]}" current "$menu"; then
  echo "    Already in $menu."
elif ask "$question"; then
  mkdir -p "$(dirname "$menu")"
  backup=""
  if [[ -f $menu ]]; then
    backup="$menu.before-kindle-send"
    cp -p "$menu" "$backup"
  fi
  status=0
  python3 -I "${menu_block[@]}" "$edit" "$menu" || status=$?
  if ((status == 1)); then
    echo "    Warning: $menu does not parse as it is; left alone." >&2
  elif ! python3 -I "${menu_block[@]}" check "$menu"; then
    if [[ -n $backup ]]; then cp -p "$backup" "$menu"; else rm -f "$menu"; fi
    echo "    Warning: the edit broke $menu, so it was put back as it was." >&2
  else
    echo "    $done $menu."
    if [[ -n $backup ]]; then echo "    Your previous file is kept as $backup."; fi
  fi
else
  not_added
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

# The repo root is the plugin; only its plugin files are copied.
copy_plugin() {
  rm -rf "$plugin_copy"
  mkdir -p "$plugin_copy"
  cp "$repo/manifest.json" "$repo"/*.qml "$repo"/*.js "$plugin_copy/"
  # The plugin runs the kindle-send bundled beside it, which finds assets/test.epub (spec §17).
  mkdir -p "$plugin_copy/bin" "$plugin_copy/assets"
  cp "$repo/bin/kindle-send" "$plugin_copy/bin/"
  cp "$repo/assets/test.epub" "$plugin_copy/assets/"
}

if ! command -v omarchy >/dev/null; then
  echo "    Not Omarchy (no 'omarchy' command); plugin not added."
else
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
  # It has no bar widget, so nothing else enables it. Enabling keeps the
  # settings already in shell.json.
  if plugin_listed && omarchy plugin enable "$plugin_id" >/dev/null; then
    echo "    Enabled. Open the picker with: omarchy-shell shell toggle $plugin_id"
  else
    echo "    Warning: Omarchy's shell did not pick the plugin up; once it is" >&2
    echo "    running, run: omarchy plugin enable $plugin_id" >&2
  fi
fi

echo "==> Nautilus"
if command -v nautilus >/dev/null; then
  # Nautilus loads extensions at start; this closes its open windows.
  nautilus -q 2>/dev/null || true
  echo "    Restarted: right-click a book and choose Send to Kindle."
else
  echo "    Nautilus not found; the right-click item shows once it is installed."
fi

echo "==> Strata"
if command -v strata >/dev/null; then
  # Strata reads its actions folder each time a menu opens.
  python3 -I "$repo/scripts/strata_action.py" "$config_dir/strata/actions" "$("$program" formats)" ||
    echo "    Warning: the Strata action was not added." >&2
else
  echo "    Strata not found; no action added."
fi

case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *) echo "Note: $bin_dir is not on your PATH in this shell." ;;
esac

echo "==> Setup"
echo "    Press SUPER + SHIFT + K to set up Books to Kindle in the Picker"
echo "    (or Omarchy menu > Books to Kindle > Settings)."
if [[ -t 0 && -t 1 ]]; then
  read -r -p "    Set up in the terminal instead? [y/N] " answer || answer=n
  if [[ ${answer,,} == y || ${answer,,} == yes ]]; then
    exec "$program" setup
  fi
fi
echo "    Or set up in the terminal instead: kindle-send setup"
