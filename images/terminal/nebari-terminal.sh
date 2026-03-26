#!/bin/bash
# Nebari terminal customization - Starship prompt init
# Sourced by /etc/profile.d/ on login shell startup.
# Controlled by NEBARI_TERMINAL_CUSTOMIZATION env var (set by KubeSpawner).

if [ "${NEBARI_TERMINAL_CUSTOMIZATION}" = "false" ]; then
    return 0 2>/dev/null || exit 0
fi

# Always use the system-wide starship config so updates take effect for all
# users without requiring them to delete their personal config. Users who
# want a custom prompt can set STARSHIP_CONFIG in their own .bashrc.
export STARSHIP_CONFIG="/etc/starship.toml"

if command -v starship &> /dev/null; then
    eval "$(starship init bash)"
fi
