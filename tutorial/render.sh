#!/usr/bin/env bash
# Render the QuakeScore tutorial and its derived files.
# Run from Git Bash:  cd tutorial && npm install && bash render.sh
# Steps: bundle -> PNG sequence (Remotion) -> H.264 encode, poster and teaser GIF (ffmpeg).
set -euo pipefail
cd "$(dirname "$0")"

MEDIA=../docs/media
FRAMES=out/frames
# On Windows, pass the bundled browser by the path this script was started from. Remotion's own
# lookup resolves directory junctions to the real path, and a long real path fails with ENOENT.
npx remotion browser ensure
BX_REL=node_modules/.remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe
BX_ARGS=()
if [ -f "$BX_REL" ] && command -v cygpath >/dev/null; then BX_ARGS=(--browser-executable="$(cygpath -m "$PWD")/$BX_REL"); fi

mkdir -p "$MEDIA" out
npx remotion bundle src/index.ts --out-dir out/bundle
rm -rf "$FRAMES"
npx remotion render out/bundle Tutorial "$FRAMES" --sequence --image-format=png "${BX_ARGS[@]}"

# Colour-accurate encode from the PNG sequence (bt709, limited range, tagged).
ffmpeg -y -framerate 30 -i "$FRAMES/element-%04d.png" \
  -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 20 -tune animation \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -movflags +faststart -map_metadata -1 -metadata title="QuakeScore tutorial" \
  "$MEDIA/quakescore_tutorial.mp4"

# Poster: stacking scene with both peaks labelled (frame 1250).
cp "$FRAMES/element-1250.png" "$MEDIA/tutorial_poster.png"

# Teaser: stacking scene only, frames 950-1235 (9.5 s at 15 fps = 143 output frames), 960 px wide, one palette.
ffmpeg -y -framerate 30 -start_number 950 -i "$FRAMES/element-%04d.png" -frames:v 143 \
  -vf "fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 "$MEDIA/tutorial_teaser.gif"

ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$MEDIA/quakescore_tutorial.mp4"
