#!/bin/bash
# Nebari terminal customization - Starship prompt init
# Sourced by /etc/profile.d/ on login shell startup.
# Controlled by NEBARI_TERMINAL_CUSTOMIZATION env var (set by KubeSpawner).

if [ "${NEBARI_TERMINAL_CUSTOMIZATION}" = "false" ]; then
    return 0 2>/dev/null || exit 0
fi

# Use the system-wide starship config. Two variants are available:
#   /etc/starship.toml       - Catppuccin Mocha (dark backgrounds)
#   /etc/starship-light.toml - Catppuccin Latte (light backgrounds)
# Default to dark. Users can switch by adding to their .bashrc:
#   export STARSHIP_CONFIG="/etc/starship-light.toml"
if [ -z "${STARSHIP_CONFIG}" ]; then
    export STARSHIP_CONFIG="/etc/starship.toml"
fi

if command -v starship &> /dev/null; then
    eval "$(starship init bash)"
    eval "$(starship completions bash)"
fi
