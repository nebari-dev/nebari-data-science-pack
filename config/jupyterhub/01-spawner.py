"""KubeSpawner configuration."""

# Storage: Disabled (requires dynamic PVC provisioning)
# TODO: Enable when storage backend is configured
c.KubeSpawner.volumes = []
c.KubeSpawner.volume_mounts = []
