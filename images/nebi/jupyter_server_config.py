# jupyter-server-proxy configuration for Nebi
# Launches `nebi serve` when the user clicks "Nebi" in the JupyterLab launcher.
# jupyter-server-proxy picks a free port, starts the process, and proxies to it.
c.ServerProxy.servers = {
    "nebi": {
        "command": ["nebi", "serve", "--port", "{port}"],
        "timeout": 20,
        "launcher_entry": {
            "title": "Nebi",
            "enabled": True,
        },
    }
}
