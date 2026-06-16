+++
title = "Shared Storage"
weight = 5
description = "Mount per-group shared directories into every user pod."
+++

The chart can mount a per-group shared directory at `/shared/<group>` in every
user pod. This needs a ReadWriteMany (RWX) `StorageClass` on the cluster.

## On NIC-managed clusters

On clusters managed by the Nebari Infrastructure Core, the RWX class is
[Longhorn](https://longhorn.io/), installed by NIC's storage layer:

```yaml
sharedStorage:
  enabled: true
  storageClass: longhorn
  size: 100Gi
```

## Clusters without an RWX class

For clusters where NIC has not yet wired up an RWX class (local dev, current
GCP and Azure paths), the chart includes a transitional in-cluster NFS server
mode:

```yaml
sharedStorage:
  enabled: true
  nfsServer:
    enabled: true
```

This depends on the `quay.io/nebari/volume-nfs` workaround image.

{{< callout type="warning" title="Transitional" >}}
The in-cluster NFS server mode is a workaround and is tracked for removal in
[issue #29](https://github.com/nebari-dev/nebari-data-science-pack/issues/29).
Prefer a real RWX `StorageClass` where one is available.
{{< /callout >}}
