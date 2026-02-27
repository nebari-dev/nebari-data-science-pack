import os

# jupyter-server-proxy configuration for Nebi
# Launches `nebi serve` when the user clicks "Nebi" in the JupyterLab launcher.
# jupyter-server-proxy picks a free port, starts the process, and proxies to it.

ICON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "icons",
    "nebi.svg",
)

c.ServerProxy.servers = {
    "nebi": {
        "command": ["nebi", "serve", "--port", "{port}"],
        "timeout": 20,
        "absolute_url": True,
        "new_browser_tab": False,
        "environment": {
            "NEBI_SERVER_BASE_PATH": "{base_url}nebi",
            "NEBI_MODE": "local",
        },
        "launcher_entry": {
            "title": "Nebi",
            "enabled": True,
            "icon_path": ICON_PATH,
        },
    }
}
