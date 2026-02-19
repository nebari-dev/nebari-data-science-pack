"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

# Home directory: Dynamic PVC provisioned per user via the cluster's default StorageClass.
# Volume configuration is handled by the jupyterhub subchart (singleuser.storage in values.yaml).
c.KubeSpawner.notebook_dir = "/home/{username}"
c.KubeSpawner.working_dir = "/home/{username}"
c.KubeSpawner.environment = {
    "HOME": "/home/{username}",
}
