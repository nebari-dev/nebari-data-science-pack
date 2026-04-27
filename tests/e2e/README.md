# e2e tests

Spins up a k3d cluster, helm-installs the chart, runs behavioral tests against the live hub.

## Run

```bash
# fresh cluster (creates + tears down)
uvx pytest tests/e2e -v

# reuse an existing cluster (skip create/delete)
K3D_CLUSTER=k3d-nebari-dev uvx pytest tests/e2e -v

# keep the cluster after the run
K3D_KEEP=1 uvx pytest tests/e2e -v
```

Logs stream live (configured in `tests/e2e/pytest.ini`).

## Requirements

`k3d`, `helm`, `kubectl` on `PATH`.
