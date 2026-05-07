"""jhub-apps integration configuration."""

# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub
import os
from urllib.parse import urlparse

from kubespawner import KubeSpawner
from jhub_apps import theme_template_paths, themes
from jhub_apps.configuration import install_jhub_apps
from z2jh import get_config

# Configure jhub-apps
# bind_url must include the real external hostname so JupyterHub constructs
# correct OAuth redirect URLs for internal services like jhub-apps.
# See: nebari's 02-spawner.py for the same pattern.
external_url = (get_config("custom.external-url", "") or "").strip()
if external_url:
    # Accept either bare hostnames (jupyter.example.com), proper URLs
    # (https://jupyter.example.com), or common typo form (https//host).
    if external_url.startswith("https//"):
        external_url = external_url.replace("https//", "https://", 1)
    elif external_url.startswith("http//"):
        external_url = external_url.replace("http//", "http://", 1)

    parsed = urlparse(external_url if "://" in external_url else f"https://{external_url}")
    host = parsed.netloc or parsed.path
    scheme = parsed.scheme or "https"
    c.JupyterHub.bind_url = f"{scheme}://{host}"
else:
    c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.default_url = "/hub/home"
c.JupyterHub.template_paths = theme_template_paths
c.JupyterHub.template_vars = themes.DEFAULT_THEME
c.JAppsConfig.jupyterhub_config_path = "/usr/local/etc/jupyterhub/jupyterhub_config.py"

# Apply JAppsConfig overrides from Helm values (jupyterhub.custom.japps-config).
# Any key in the dict is set as an attribute on c.JAppsConfig, e.g.:
#   japps-config:
#     app_title: "My Launcher"
#     service_workers: 2
#     allowed_frameworks: ["panel", "streamlit"]
japps_config = get_config("custom.japps-config", {})
for key, value in japps_config.items():
    setattr(c.JAppsConfig, key, value)

# Install jhub-apps (sets up service, roles, etc.)
c = install_jhub_apps(c, spawner_to_subclass=KubeSpawner)

# Forward JUPYTERHUB_OIDC_CLIENT_SECRET to the jhub-apps subprocess so that
# 03-nebi-envs.py (which is re-evaluated inside the subprocess via
# get_jupyterhub_config()) can read it for Keycloak token exchange.
_oidc_secret = os.environ.get("JUPYTERHUB_OIDC_CLIENT_SECRET", "")
if _oidc_secret:
    for svc in c.JupyterHub.services:
        if svc.get("name") == "japps":
            svc.setdefault("environment", {})["JUPYTERHUB_OIDC_CLIENT_SECRET"] = _oidc_secret
            break
