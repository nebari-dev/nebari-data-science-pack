"""KubeSpawner configuration."""
# ruff: noqa: F821 - `c` is a magic global provided by JupyterHub

# Home directory: Dynamic PVC per user via the cluster's default StorageClass.
# We configure volumes here instead of via singleuser.storage in values.yaml because
# jhub-apps' JHubSpawner expects volumes as a list, but the subchart's dynamic storage
# generates a dict, causing a TraitError on startup.
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
        "mountPath": "/home/{username}",
    },
]

c.KubeSpawner.notebook_dir = "/home/{username}"
c.KubeSpawner.working_dir = "/home/{username}"
c.KubeSpawner.environment = {
    "HOME": "/home/{username}",
}
