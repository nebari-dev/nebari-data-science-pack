# nebari-data-science-pack

[![Lint](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/lint.yaml/badge.svg)](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/lint.yaml)
[![Test](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/test.yaml/badge.svg)](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/test.yaml)
[![Release](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/release.yaml/badge.svg)](https://github.com/nebari-dev/nebari-data-science-pack/actions/workflows/release.yaml)

A Helm chart for deploying JupyterHub with [jhub-apps](https://github.com/nebari-dev/jhub-apps) on Kubernetes.

## Features

- JupyterHub with Nebari's custom images
- jhub-apps integration for deploying data science applications
- Dummy authenticator for local development (OAuth/Keycloak configurable for production)
- Optional shared storage (RWX PVC)

## Quick Start

### Install from Helm Repository

```bash
helm repo add nebari https://nebari-dev.github.io/nebari-data-science-pack
helm repo update
helm install nebari nebari/nebari-data-science-pack
```

### Install from Source

```bash
git clone https://github.com/nebari-dev/nebari-data-science-pack.git
cd nebari-data-science-pack
helm dependency update
helm install nebari . --namespace default
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

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

