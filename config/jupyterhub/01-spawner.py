"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

# Storage: Disabled (requires dynamic PVC provisioning)
# TODO: Enable when storage backend is configured
c.KubeSpawner.volumes = []
c.KubeSpawner.volume_mounts = []
