"""jhub-apps integration configuration."""

# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub
from kubespawner import KubeSpawner
from jhub_apps import theme_template_paths, themes
from jhub_apps.configuration import install_jhub_apps
from z2jh import get_config

# Configure jhub-apps
# bind_url must include the real external hostname so JupyterHub constructs
# correct OAuth redirect URLs for internal services like jhub-apps.
# See: nebari's 02-spawner.py for the same pattern.
domain = get_config("custom.external-url", "")
if domain:
    c.JupyterHub.bind_url = f"https://{domain}"
else:
    c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.default_url = "/hub/home"
c.JupyterHub.template_paths = theme_template_paths
c.JupyterHub.template_vars = themes.DEFAULT_THEME
c.JAppsConfig.jupyterhub_config_path = "/usr/local/etc/jupyterhub/jupyterhub_config.py"
c.JAppsConfig.hub_host = "hub"
c.JAppsConfig.service_workers = 4

# Install jhub-apps (sets up service, roles, etc.)
c = install_jhub_apps(c, spawner_to_subclass=KubeSpawner)
