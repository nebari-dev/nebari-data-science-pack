#!/usr/bin/env bash
# Inject @font-face and font-load handler into JupyterLab's index.html.
# xterm.js uses Canvas rendering and won't re-render when a web font loads.
# We preload the font and trigger a window resize after fonts are ready,
# which forces xterm.js to re-measure and re-render with the correct font.
set -euo pipefail

INDEX_HTML="${1:?Usage: inject-font.sh <path-to-index.html>}"

python3 -c "
import sys
path = sys.argv[1]
injection = '''<link rel=\"preload\" href=\"../static/lab/fonts/FiraCodeNerdFontMono-Regular.ttf\" as=\"font\" type=\"font/ttf\" crossorigin><style>@font-face{font-family:\"FiraCode Nerd Font\";src:url(\"../static/lab/fonts/FiraCodeNerdFontMono-Regular.ttf\") format(\"truetype\");font-weight:400;font-display:block}@font-face{font-family:\"FiraCode Nerd Font\";src:url(\"../static/lab/fonts/FiraCodeNerdFontMono-Bold.ttf\") format(\"truetype\");font-weight:700;font-display:block}</style><script>document.fonts.ready.then(function(){setTimeout(function(){window.dispatchEvent(new Event(\"resize\"))},100)})</script>'''
with open(path, 'r') as f:
    html = f.read()
html = html.replace('</head>', injection + '</head>', 1)
with open(path, 'w') as f:
    f.write(html)
print(f'Font injection complete: {path}')
" "$INDEX_HTML"
