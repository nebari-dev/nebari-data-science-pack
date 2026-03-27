#!/usr/bin/env bash
# Download and install Fira Code Nerd Font (TTF) for JupyterLab terminal.
# Called during Docker build.
set -euo pipefail
set -x

NERD_FONTS_VERSION="v3.4.0"
JUPYTERLAB_STATIC_DIR="${1:?Usage: install-fonts.sh <jupyterlab-static-dir>}"
FONT_DIR="${JUPYTERLAB_STATIC_DIR}/fonts"

mkdir -p "${FONT_DIR}"

DOWNLOAD_URL="https://github.com/ryanoasis/nerd-fonts/releases/download/${NERD_FONTS_VERSION}/FiraCode.zip"

TMP_DIR=$(mktemp -d)
curl -fsSL -o "${TMP_DIR}/FiraCode.zip" "${DOWNLOAD_URL}"

# Extract only the Mono variants (fixed-width glyphs, required for terminals)
unzip -q "${TMP_DIR}/FiraCode.zip" \
    'FiraCodeNerdFontMono-Regular.ttf' \
    'FiraCodeNerdFontMono-Bold.ttf' \
    -d "${TMP_DIR}"

cp "${TMP_DIR}/FiraCodeNerdFontMono-Regular.ttf" "${FONT_DIR}/"
cp "${TMP_DIR}/FiraCodeNerdFontMono-Bold.ttf" "${FONT_DIR}/"

# Also install as system font so Chromium's OffscreenCanvas can resolve it.
# OffscreenCanvas uses the system font stack, not CSS @font-face.
mkdir -p /usr/local/share/fonts/firacode-nerd
cp "${TMP_DIR}/FiraCodeNerdFontMono-Regular.ttf" /usr/local/share/fonts/firacode-nerd/
cp "${TMP_DIR}/FiraCodeNerdFontMono-Bold.ttf" /usr/local/share/fonts/firacode-nerd/
fc-cache -f /usr/local/share/fonts/firacode-nerd

rm -rf "${TMP_DIR}"
echo "Fira Code Nerd Font installed to ${FONT_DIR} and /usr/local/share/fonts/"
