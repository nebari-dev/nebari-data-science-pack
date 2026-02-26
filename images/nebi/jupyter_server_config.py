import os

# jupyter-server-proxy configuration for Nebi
# Launches `nebi serve` when the user clicks "Nebi" in the JupyterLab launcher.
# jupyter-server-proxy picks a free port, starts the process, and proxies to it.

ICON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "icons",
    "nebi.svg",
)

# WORKAROUND for https://github.com/nebari-dev/jupyterlab-launchpad/issues/73
# jupyterlab-launchpad doesn't render icon_path for server-proxy entries.
# This loads custom CSS that injects the icon via background-image.
# When the bug is fixed, remove this line AND:
#   - delete images/nebi/custom/ directory
#   - remove the COPY nebi/custom line from images/Dockerfile
c.LabApp.custom_css = True

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
