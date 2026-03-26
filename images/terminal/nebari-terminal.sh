#!/bin/bash
# Nebari terminal customization - Starship prompt init
# Sourced by /etc/profile.d/ on login shell startup.
# Controlled by NEBARI_TERMINAL_CUSTOMIZATION env var (set by KubeSpawner).

if [ "${NEBARI_TERMINAL_CUSTOMIZATION}" = "false" ]; then
    return 0 2>/dev/null || exit 0
fi

# Use system-wide starship config as fallback if user has no personal config
if [ ! -f "${HOME}/.config/starship.toml" ]; then
    export STARSHIP_CONFIG="/etc/starship.toml"
fi

if command -v starship &> /dev/null; then
    eval "$(starship init bash)"
fi
