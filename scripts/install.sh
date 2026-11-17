#!/usr/bin/env bash
# Books to Kindle's optional extras. Needs no root. Run it from the plugin folder:
#
#   ~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh [--yes]
#   ~/.config/omarchy/plugins/sorydi3.kindle-send/scripts/install.sh --remove [--purge]
#
# The plugin works without them: `omarchy plugin add` installs it. Asking before
# each one, this adds the ~/.local/bin/kindle-send link to the bundled program,
# the Nautilus right-click item (with nautilus-python), the Strata action (with
# Strata), the SUPER + SHIFT + K binding and the Books to Kindle menu entries.
# With no terminal to ask in, it changes nothing. Each edited file is backed up
# first (<file>.before-kindle-send), and the lines it adds sit between
# ">>> kindle-send" / "<<< kindle-send" markers. Safe to run again: what is up
# to date is left as it is, and an older block is replaced in place.
#
#   --yes     add the extras without asking
#   --remove  remove the extras; keeps the Settings, the app password and the Send history
#   --purge   remove the extras and delete the Settings, the app password and the Send history
set -euo pipefail

mode=add
asking=ask
for argument in "$@"; do
  case "$argument" in
    --yes | -y) asking=yes ;;
    --remove) [[ $mode == purge ]] || mode=remove ;;
    --purge) mode=purge ;;
    -h | --help)
      awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
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
program="$repo/bin/kindle-send"
bin_dir="$HOME/.local/bin"
link="$bin_dir/kindle-send"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}"
share_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/kindle-send"
settings_dir="$config_dir/kindle-send"
# Where an install from before the plugin was published copied the program.
old_program="$share_dir/kindle-send/bin/kindle-send"
nautilus_dir="$share_dir/nautilus-python/extensions"
nautilus_ext="$nautilus_dir/kindle-send.py"
nautilus_python="${KINDLE_SEND_NAUTILUS_PYTHON:-/usr/lib/nautilus/extensions-4/libnautilus-python.so}"
strata_actions="$config_dir/strata/actions"
strata_action="$strata_actions/kindle-send"
bindings="$config_dir/hypr/bindings.lua"
menu="$config_dir/omarchy/extensions/omarchy-menu.jsonc"
bind_start="-- >>> kindle-send keybinding (added by scripts/install.sh) >>>"
bind_line="o.bind(\"SUPER + SHIFT + K\", \"Books to Kindle\", \"omarchy-shell shell toggle $plugin_id\")"
bind_end="-- <<< kindle-send <<<"
menu_block=("$repo/scripts/menu_block.py")

# ---- telling what is ours

# ours_command: whether ~/.local/bin/kindle-send is this plugin's (a link to a
# bundled or older copied kindle-send, or an older install's copy), not someone else's.
ours_command() {
  if [[ -L $link ]]; then
    local target
    target=$(readlink "$link")
    [[ $link -ef $program || $target == "$old_program" || $target == */$plugin_id/bin/kindle-send ]] && return 0
  elif [[ ! -f $link ]]; then
    return 1
  fi
  [[ -f $link ]] && grep -qF "PLUGIN_ID = \"$plugin_id\"" "$link"
}

# ours_nautilus_ext: whether the Nautilus extension file is this plugin's (every
# version of it names the plugin), not someone else's kindle-send.py.
ours_nautilus_ext() {
  [[ -f $nautilus_ext ]] && grep -qF "PLUGIN_ID = \"$plugin_id\"" "$nautilus_ext"
}

ours_strata_action() {
  [[ -f $strata_action/action.toml ]] && grep -qF 'args = ["pick", "{paths}"]' "$strata_action/action.toml"
}

has_binding_block() {
  [[ -f $bindings ]] && grep -qxF -- "$bind_start" "$bindings"
}

binding_block_whole() {
  awk -v start="$bind_start" -v end="$bind_end" '
    $0 == start { inside = 1; next }
    inside && $0 == end { found = 1; exit }
    END { exit !found }
  ' "$bindings"
}

# binding_block_current: whether the block holds exactly this version's binding.
binding_block_current() {
  awk -v start="$bind_start" -v end="$bind_end" -v line="$bind_line" '
    $0 == start { inside = 1; next }
    inside && $0 == end { exit }
    inside { block = block $0 "\n" }
    END { exit block != line "\n" }
  ' "$bindings"
}

# rewrite_bindings AWK_PROGRAM: run it over the bindings file, in place.
rewrite_bindings() {
  awk -v start="$bind_start" -v end="$bind_end" -v line="$bind_line" "$1" "$bindings" >"$bindings.kindle-send-tmp"
  cat "$bindings.kindle-send-tmp" >"$bindings"
  rm -f "$bindings.kindle-send-tmp"
}

# ---- --remove and --purge

if [[ $mode != add ]]; then
  echo "==> Keybinding"
  if ! has_binding_block; then
    echo "    None was added."
  elif ! binding_block_whole; then
    echo "    Warning: the kindle-send block in $bindings has no end marker; left alone." >&2
  else
    # The block, and the one blank line put before it.
    rewrite_bindings '
      inside      { if ($0 == end) inside = 0; next }
      $0 == start { inside = 1; for (i = 1; i < blanks; i++) print ""; blanks = 0; next }
      $0 == ""    { blanks++; next }
                  { for (i = 0; i < blanks; i++) print ""; blanks = 0; print }
      END         { for (i = 0; i < blanks; i++) print "" }'
    echo "    Removed from $bindings."
  fi

  echo "==> Omarchy menu"
  if [[ -f $menu ]] && grep -qF -- "// >>> kindle-send menu" "$menu"; then
    before="$menu.kindle-send-remove"
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
    echo "    None were added."
  fi

  echo "==> Command"
  if ours_command; then
    rm -f "$link"
    echo "    Removed $link."
  elif [[ -e $link || -L $link ]]; then
    echo "    $link is not Books to Kindle's; left alone."
  else
    echo "    No link."
  fi

  echo "==> Right-click items"
  if ours_nautilus_ext; then
    rm -f "$nautilus_ext"
    echo "    Removed $nautilus_ext."
    if command -v nautilus >/dev/null; then
      nautilus -q 2>/dev/null || true
    fi
  elif [[ -e $nautilus_ext || -L $nautilus_ext ]]; then
    echo "    $nautilus_ext is not Books to Kindle's; left alone."
  fi
  if ours_strata_action; then
    rm -rf "$strata_action"
    echo "    Removed $strata_action."
  elif [[ -e $strata_action ]]; then
    echo "    $strata_action is not Books to Kindle's; left alone."
  fi

  echo "==> Settings, app password and Send history"
  if [[ $mode == purge ]]; then
    rm -rf "$settings_dir" "$state_dir"
    if command -v secret-tool >/dev/null; then
      secret-tool clear service kindle-send 2>/dev/null || true
    else
      echo "    secret-tool not found; the app password may still be in the keyring." >&2
    fi
    echo "    Deleted $settings_dir, the app password and $state_dir."
  else
    echo "    Kept: $settings_dir, the app password in the keyring and $state_dir."
    echo "    Run with --purge to delete them too."
  fi

  echo "The extras are removed. To remove the plugin itself: omarchy plugin remove $plugin_id"
  exit 0
fi

# ---- adding the extras

echo "==> Checking dependencies"
missing=()
for tool in python3 secret-tool; do
  command -v "$tool" >/dev/null || missing+=("$tool")
done
if ((${#missing[@]})); then
  declare -A package=([python3]=python [secret-tool]=libsecret)
  for tool in "${missing[@]}"; do
    echo "Missing: $tool. Install it with: sudo pacman -S ${package[$tool]}" >&2
  done
  echo "Nothing was changed. Run this script again once they are there." >&2
  exit 1
fi
echo "    python3, secret-tool: found"
command -v ebook-convert >/dev/null || echo "    Optional: sudo pacman -S calibre to send EPUB over USB"

if [[ $asking == ask && ! -t 0 ]]; then
  echo "    No terminal to ask in, so nothing is changed. Run again in a terminal, or with --yes."
fi

# ask QUESTION: whether to make one change, from --yes or the terminal.
ask() {
  local answer
  [[ $asking == yes ]] && return 0
  [[ -t 0 ]] || return 1
  read -r -p "    $1 [y/N] " answer || return 1
  [[ ${answer,,} == y || ${answer,,} == yes ]]
}

not_added() {
  if [[ $asking == ask && ! -t 0 ]]; then
    echo "    Not added: no terminal to ask in."
  else
    echo "    Not added."
  fi
}

echo "==> Command: $link"
linked=no
if [[ -L $link && $link -ef $program ]]; then
  echo "    Already links to $program."
  linked=yes
elif [[ -e $link || -L $link ]] && ! ours_command; then
  echo "    $link is not Books to Kindle's; left alone."
else
  question="Link $link to $program, for the terminal and the right-click items?"
  [[ -e $link || -L $link ]] && question="Replace the older $link with a link to $program?"
  if ask "$question"; then
    mkdir -p "$bin_dir"
    rm -f "$link"
    ln -s "$program" "$link"
    echo "    Linked."
    linked=yes
  else
    not_added
  fi
fi

echo "==> Nautilus right-click item"
nautilus_changed=no
if [[ ! -e $nautilus_python ]]; then
  echo "    nautilus-python is not installed; skipped (sudo pacman -S nautilus-python adds it)."
elif [[ $linked == no ]]; then
  echo "    Skipped: the right-click items need the kindle-send link."
elif [[ -f $nautilus_ext ]] && cmp -s "$repo/nautilus/kindle-send.py" "$nautilus_ext"; then
  echo "    Already in $nautilus_dir."
else
  question="Add the Nautilus right-click item to $nautilus_dir?"
  [[ -f $nautilus_ext ]] && question="Update the Nautilus right-click item in $nautilus_dir?"
  if ask "$question"; then
    mkdir -p "$nautilus_dir"
    install -m 644 "$repo/nautilus/kindle-send.py" "$nautilus_ext"
    echo "    $nautilus_ext"
    nautilus_changed=yes
  else
    not_added
  fi
fi

echo "==> Strata right-click action"
if ! command -v strata >/dev/null; then
  echo "    Strata not found; skipped."
elif [[ $linked == no ]]; then
  echo "    Skipped: the right-click items need the kindle-send link."
elif ! formats="$("$program" formats)"; then
  echo "    Warning: kindle-send did not list its formats; the Strata action was not added." >&2
elif python3 -I "$repo/scripts/strata_action.py" --current "$strata_actions" "$formats"; then
  echo "    Already in $strata_actions."
elif [[ -e $strata_action ]] && ! ours_strata_action; then
  echo "    $strata_action is not Books to Kindle's; left alone."
elif ask "Add the Strata right-click action to $strata_actions?"; then
  # Strata reads its actions folder each time a menu opens.
  python3 -I "$repo/scripts/strata_action.py" "$strata_actions" "$formats" ||
    echo "    Warning: the Strata action was not added." >&2
else
  not_added
fi

echo "==> Keybinding SUPER + SHIFT + K"
if [[ ! -f $bindings ]] || ! grep -q 'o\.bind' "$bindings"; then
  echo "    No Omarchy bindings file at $bindings; nothing added."
elif has_binding_block && ! binding_block_whole; then
  echo "    Warning: the kindle-send block in $bindings has no end marker; left alone." >&2
elif has_binding_block && binding_block_current; then
  echo "    Already in $bindings."
elif has_binding_block; then
  if ask "Replace the older SUPER + SHIFT + K binding in $bindings?"; then
    cp -p "$bindings" "$bindings.before-kindle-send"
    rewrite_bindings '
      inside      { if ($0 == end) { inside = 0; print }; next }
      $0 == start { print; print line; inside = 1; next }
                  { print }'
    echo "    Updated in $bindings. Your previous file is kept as $bindings.before-kindle-send."
  else
    not_added
  fi
elif ask "Add SUPER + SHIFT + K (open the Picker) to $bindings?"; then
  cp -p "$bindings" "$bindings.before-kindle-send"
  printf '\n%s\n%s\n%s\n' "$bind_start" "$bind_line" "$bind_end" >>"$bindings"
  echo "    Added. Your previous file is kept as $bindings.before-kindle-send."
else
  not_added
fi

echo "==> Omarchy menu: Books to Kindle, and Books to Kindle > Settings"
edit=add question="Add them to $menu?" done="Added to"
if [[ -f $menu ]] && grep -qF -- "// >>> kindle-send menu" "$menu"; then
  # An older install's block (from before the rename, or with a "Setup" entry running the terminal wizard)
  # is swapped in place.
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

if [[ $nautilus_changed == yes ]]; then
  echo "==> Nautilus"
  if command -v nautilus >/dev/null; then
    # Nautilus loads extensions at start; this closes its open windows.
    nautilus -q 2>/dev/null || true
    echo "    Restarted: right-click a book and choose Send to Kindle."
  else
    echo "    Nautilus not found; the right-click item shows once it is installed."
  fi
fi

if [[ $linked == yes ]]; then
  case ":$PATH:" in
    *":$bin_dir:"*) ;;
    *) echo "Note: $bin_dir is not on your PATH in this shell." ;;
  esac
fi

echo "==> Setup"
opens="    Open the Picker from the Books to Kindle bar widget"
has_binding_block && binding_block_current && opens="$opens (or press SUPER + SHIFT + K)"
echo "$opens to set it up in Settings."
setup="$program setup"
[[ $linked == yes ]] && setup="kindle-send setup"
if [[ -t 0 && -t 1 ]]; then
  read -r -p "    Set up in the terminal instead? [y/N] " answer || answer=n
  if [[ ${answer,,} == y || ${answer,,} == yes ]]; then
    exec "$program" setup
  fi
fi
echo "    Or set up in the terminal instead: $setup"
