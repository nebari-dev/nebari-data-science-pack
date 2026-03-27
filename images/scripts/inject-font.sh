#!/usr/bin/env bash
# Inject Nerd Font loading into JupyterLab's index.html.
set -euo pipefail

INDEX_HTML="${1:?Usage: inject-font.sh <path-to-index.html>}"
LOADER_JS="${2:?Usage: inject-font.sh <index.html> <nerd-font-loader.js>}"

python3 -c "
import sys

index_path = sys.argv[1]
js_path = sys.argv[2]

# Read the JS loader
with open(js_path) as f:
    js_code = f.read().strip()

# Build the injection: @font-face CSS + inline JS loader
injection = (
    '<link rel=\"preload\" href=\"/static/lab/fonts/FiraCodeNerdFontMono-Regular.ttf\" as=\"font\" type=\"font/ttf\" crossorigin>'
    '<style>'
    '@font-face{font-family:\"FiraCode Nerd Font\";src:url(\"/static/lab/fonts/FiraCodeNerdFontMono-Regular.ttf\") format(\"truetype\");font-weight:400;font-display:swap}'
    '@font-face{font-family:\"FiraCode Nerd Font\";src:url(\"/static/lab/fonts/FiraCodeNerdFontMono-Bold.ttf\") format(\"truetype\");font-weight:700;font-display:swap}'
    '</style>'
    '<script>' + js_code + '</script>'
)

with open(index_path) as f:
    html = f.read()
html = html.replace('</head>', injection + '</head>', 1)
with open(index_path, 'w') as f:
    f.write(html)
print(f'Font injection complete: {index_path}')
" "$INDEX_HTML" "$LOADER_JS"
