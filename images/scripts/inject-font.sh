#!/usr/bin/env bash
# Inject Nerd Font loading into JupyterLab's index.html.
#
# Root cause: xterm.js uses OffscreenCanvas to measure font metrics.
# OffscreenCanvas does NOT have access to fonts loaded via the FontFace
# JS API (document.fonts.add). It only sees CSS @font-face fonts.
#
# Solution: use @font-face in a <style> tag (makes font available to
# OffscreenCanvas) + preload hint (starts download early) + a script
# that waits for fonts to load then triggers xterm.js re-measurement
# by dispatching a resize event.
set -euo pipefail

INDEX_HTML="${1:?Usage: inject-font.sh <path-to-index.html>}"

python3 -c '
import sys

path = sys.argv[1]

injection = (
    # Preload for early high-priority fetch
    "<link rel=\"preload\" href=\"../static/lab/fonts/FiraCodeNerdFontMono-Regular.ttf\" as=\"font\" type=\"font/ttf\" crossorigin>"
    # CSS @font-face — this is what makes the font available to OffscreenCanvas
    "<style>"
    "@font-face{font-family:\"FiraCode Nerd Font\";src:url(\"../static/lab/fonts/FiraCodeNerdFontMono-Regular.ttf\") format(\"truetype\");font-weight:400;font-display:swap}"
    "@font-face{font-family:\"FiraCode Nerd Font\";src:url(\"../static/lab/fonts/FiraCodeNerdFontMono-Bold.ttf\") format(\"truetype\");font-weight:700;font-display:swap}"
    "</style>"
    # After font loads, trigger resize so xterm.js re-measures
    "<script>document.fonts.ready.then(function(){setTimeout(function(){window.dispatchEvent(new Event(\"resize\"))},100)})</script>"
)

with open(path, "r") as f:
    html = f.read()
html = html.replace("</head>", injection + "</head>", 1)
with open(path, "w") as f:
    f.write(html)
print(f"Font injection complete: {path}")
' "$INDEX_HTML"
