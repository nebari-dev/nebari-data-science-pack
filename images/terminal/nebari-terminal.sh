#!/bin/bash
# Nebari terminal customization - Starship prompt init
# Sourced by /etc/profile.d/ on login shell startup.
# Controlled by NEBARI_TERMINAL_CUSTOMIZATION env var (set by KubeSpawner).

if [ "${NEBARI_TERMINAL_CUSTOMIZATION}" = "false" ]; then
    return 0 2>/dev/null || exit 0
fi

# Use ANSI color names so the prompt adapts to JupyterLab's
# terminal palette automatically (light/dark theme switch).
# Users can override by setting STARSHIP_CONFIG in their .bashrc.
if [ -z "${STARSHIP_CONFIG}" ]; then
    export STARSHIP_CONFIG="/etc/starship.toml"
fi

if command -v starship &> /dev/null; then
    eval "$(starship init bash)"
    eval "$(starship completions bash)"
fi
