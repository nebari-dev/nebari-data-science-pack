"""jhub-apps integration configuration."""
from kubespawner import KubeSpawner
from jhub_apps import theme_template_paths, themes
from jhub_apps.configuration import install_jhub_apps

# Configure jhub-apps
c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.default_url = "/hub/home"
c.JupyterHub.template_paths = theme_template_paths
c.JupyterHub.template_vars = themes.DEFAULT_THEME
c.JAppsConfig.jupyterhub_config_path = "/usr/local/etc/jupyterhub/jupyterhub_config.py"
c.JAppsConfig.hub_host = "hub"
c.JAppsConfig.service_workers = 4

# Install jhub-apps (sets up service, roles, etc.)
c = install_jhub_apps(c, spawner_to_subclass=KubeSpawner)
