# e2e tests

Spins up a kind cluster, helm-installs the chart, runs behavioral tests against the live hub.

kind (not k3d) — kind nodes are full ubuntu containers, so the chart's
`installClient` DaemonSet (apt-based) can install nfs-common, which is
needed for the in-cluster NFS server feature. k3d's busybox-on-scratch
nodes have no package manager.

## Run

```bash
# fresh cluster (creates + tears down)
uvx pytest tests/e2e -v

# reuse an existing cluster (skip create/delete)
KIND_CLUSTER=my-cluster uvx pytest tests/e2e -v

# keep the cluster after the run
KIND_KEEP=1 uvx pytest tests/e2e -v
```

Logs stream live (configured in `tests/e2e/pytest.ini`).

## Requirements

`kind`, `helm`, `kubectl` on `PATH`.
