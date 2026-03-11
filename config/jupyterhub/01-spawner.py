"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

from z2jh import get_config

# Home directory: Dynamic PVC per user via the cluster's default StorageClass.
# We configure volumes here instead of via singleuser.storage in values.yaml because
# jhub-apps' JHubSpawner expects volumes as a list, but the subchart's dynamic storage
# generates a dict, causing a TraitError on startup.
#
# Using fixed /home/jovyan mount path because {username} expands differently in
# KubeSpawner (escaped slug) vs base Spawner traits like notebook_dir (raw username),
# causing a path mismatch when usernames contain special characters (e.g. emails).
# Each user still gets an isolated PVC via claim-{username}.
c.KubeSpawner.storage_pvc_ensure = True
c.KubeSpawner.storage_capacity = "10Gi"
c.KubeSpawner.storage_access_modes = ["ReadWriteOnce"]
c.KubeSpawner.volumes = [
    {
        "name": "home",
        "persistentVolumeClaim": {
            "claimName": "claim-{username}",
        },
    },
]
c.KubeSpawner.volume_mounts = [
    {
        "name": "home",
        "mountPath": "/home/jovyan",
    },
]

c.KubeSpawner.notebook_dir = "/home/jovyan"
c.KubeSpawner.working_dir = "/home/jovyan"

# Nebi remote server URL — when set, JupyterLab pods auto-connect to the
# Nebi team server using the user's Keycloak IdToken cookie.
# Read from JupyterHub custom config (set via values.yaml jupyterhub.custom.nebi-remote-url).
nebi_remote_url = get_config("custom.nebi-remote-url", "")

env = {
    "HOME": "/home/jovyan",
}
if nebi_remote_url:
    env["NEBI_REMOTE_URL"] = nebi_remote_url

c.KubeSpawner.environment = env
