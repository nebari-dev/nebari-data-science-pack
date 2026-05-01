# nebari-data-science-pack

[![Lint](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/lint.yaml/badge.svg)](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/lint.yaml)
[![Test](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/test.yaml/badge.svg)](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/test.yaml)
[![Release](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/release.yaml/badge.svg)](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/release.yaml)

A Helm chart for deploying JupyterHub with [jhub-apps](https://github.com/nebari-dev/jhub-apps) on Kubernetes.

## Features

- JupyterHub with Nebari's custom images
- jhub-apps integration for deploying data science applications
- Dummy authenticator for local development (OAuth/Keycloak configurable for production)

## Quick Start

### Install from Helm Repository

```bash
helm repo add nebari https://nebari-dev.github.io/nebari-data-science-pack
helm repo update
helm install data-science-pack nebari/nebari-data-science-pack
```

### Install from Source

```bash
git clone https://github.com/nebari-dev/nebari-data-science-pack.git
cd nebari-data-science-pack
helm dependency update
helm install data-science-pack . --namespace default
```

### Access JupyterHub

```bash
kubectl port-forward svc/proxy-public 8000:80
```

Open http://localhost:8000 - with dummy auth, any username/password works.

## Local Development

Prerequisites: [Docker](https://docs.docker.com/get-docker/), [ctlptl](https://github.com/tilt-dev/ctlptl), [Tilt](https://docs.tilt.dev/install.html)

```bash
# Start local k3d cluster + Tilt dev loop
make up

# Tilt UI: http://localhost:10350
# JupyterHub: http://localhost:8000

# Tear down
make down
```

## Configuration

See `values.yaml` for all configuration options. The chart wraps the [JupyterHub Helm chart](https://z2jh.jupyter.org/) - all `jupyterhub.*` values are passed through.

## Shared Storage

Per-group shared directories (`/shared/<group>` in every user pod) need a
ReadWriteMany volume. The chart does **not** ship a storage backend by default
— bring your own RWX `StorageClass` and point the chart at it:

```yaml
sharedStorage:
  enabled: true
  storageClass: <your-rwx-class>   # e.g. longhorn, efs-sc, azurefile-csi
  size: 100Gi
```

Recommended options by environment:

| Environment | RWX backend | Notes |
|-------------|-------------|-------|
| Hetzner / on-prem | [Longhorn](https://longhorn.io/) | Provisioned by NIC's storage layer |
| AWS | [EFS CSI driver](https://github.com/kubernetes-sigs/aws-efs-csi-driver) | RWX via EFS |
| GCP | [Filestore CSI driver](https://cloud.google.com/filestore) | RWX via Filestore |
| Azure | [Azure Files CSI driver](https://github.com/kubernetes-sigs/azurefile-csi-driver) | RWX via Azure Files |
| Generic (have NFS) | [`nfs-subdir-external-provisioner`](https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner) | Point it at any existing NFS export |

For clusters that cannot provide an RWX class natively, the chart includes a
transitional `sharedStorage.nfsServer.enabled=true` mode that runs an
in-cluster NFS server pod. This is being tracked for removal in
[issue #29](https://github.com/nebari-dev/nebari-data-science-pack/issues/29) —
prefer one of the options above for new deployments.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    proxy                         │
│              (configurable-http-proxy)           │
└─────────────────┬───────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
┌───────────┐          ┌─────────────┐
│    hub    │◄────────►│  jhub-apps  │
│ (JupyterHub)         │  (service)  │
└─────┬─────┘          └─────────────┘
      │
      ▼
┌─────────────┐
│ user pods   │
│ (notebooks) │
└─────────────┘
```

## CI/CD

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `lint.yaml` | push/PR | Helm lint and template validation |
| `test.yaml` | push/PR | Full deployment test on k3d |
| `release.yaml` | push to main | Publish chart to GitHub Pages |

## Releasing

To release a new version:

1. Update `version` in `Chart.yaml`
2. Push to `main`
3. The release workflow automatically:
   - Creates a GitHub release tagged with the chart version
   - Publishes the chart to GitHub Pages

**Note:** Enable GitHub Pages on the `gh-pages` branch in repo settings after the first release.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

