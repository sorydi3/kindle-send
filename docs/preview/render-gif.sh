#!/usr/bin/env bash
# Renders docs/demo.gif, the README's demo, offscreen: the plugin's real bar
# widget and Picker played through demo.qml's timeline (open from the bar,
# filter, mark two Books, switch one to USB, send, the notification card,
# Settings, close), grabbed frame by frame and put together with ffmpeg. It
# runs in harness.sh's throwaway world: demo Books and Settings, a stand-in
# keyring, the offscreen platform, a stand-in Service; nothing is sent.
#
#   docs/preview/render-gif.sh [out.gif]   default: docs/demo.gif
#   PREVIEW_FPS=<n>                        frames per second (default 12)
#   OMARCHY_THEME_DIR=<dir>                another theme folder (colors.toml, shell.toml, backgrounds/)
#   PREVIEW_KEEP=1                         keep the throwaway folder, frames included
set -euo pipefail

source "$(dirname "$0")/harness.sh"
out=$(realpath -m "${1:-$repo/docs/demo.gif}")
fps=${PREVIEW_FPS:-12}
frames=$work/frames
mkdir -p "$frames"

if ! run_scene "$here/demo.qml" 300 PREVIEW_OUT="$frames" PREVIEW_FPS="$fps"; then
  echo "No frames were written." >&2
  exit 1
fi

# Frames are grabbed at twice the size, then scaled down: smoother text. One
# palette for the whole film; the rectangle diff mode keeps unchanged parts
# of each frame (most of the wallpaper) out of the file.
scale="scale=1200:-1:flags=lanczos"
ffmpeg -v error -y -framerate "$fps" -i "$frames/frame-%04d.png" \
  -vf "$scale,palettegen=max_colors=256:stats_mode=full" "$work/palette.png"
ffmpeg -v error -y -framerate "$fps" -i "$frames/frame-%04d.png" -i "$work/palette.png" \
  -lavfi "$scale [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 "$out"
echo "Wrote $out"
