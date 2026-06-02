---
title: Configuration guide
description: Walkthrough of the chart values you'll most often touch after install — NebariApp routing, profiles, shared storage, Keycloak OAuth, Keycloak RBAC bootstrap, Nebi integration.
sidebar_position: 3
---

# Configuration guide

Once the pack is installed (see [Deploy the pack](./deploy)), this
page walks through the chart values you're most likely to tune. The
full reference — every chart value with its type, default, and
description — lives at
[Reference → `values.yaml` reference](../references/values).

:::note[Defaults reflect chart v0.1.0-alpha.13]

Image tags, subchart versions, and other defaults cited below match
[`Chart.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/Chart.yaml)
and [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
on `main`. Check the repo for the latest pinned versions.

:::

## NebariApp / external access

When `nebariapp.enabled: true`, the chart creates a NebariApp CR that
the nebari-operator picks up to provision Envoy Gateway routing, TLS,
and (optionally) Keycloak OIDC.

| Value | Default | Description |
|---|---|---|
| `nebariapp.enabled` | `true` | Create the NebariApp resource for routing / TLS / auth |
| `nebariapp.hostname` | — | Hostname for the hub (required when `nebariapp.enabled`) |
| `nebariapp.service.name` | `proxy-public` | JupyterHub proxy service |
| `nebariapp.service.port` | `80` | Proxy service port |
| `nebariapp.auth.enabled` | `true` | Require Keycloak OIDC for external access |
| `nebariapp.auth.redirectURI` | `/hub/oauth_callback` | OAuth callback — must match the hub's, not Envoy's, callback path |
| `nebariapp.auth.enforceAtGateway` | `false` | Run Envoy's OIDC filter at the gateway (off by default — see warning below) |
| `nebariapp.auth.forwardAccessToken` | `false` | Have Envoy forward the upstream Bearer token (off — hub owns the OAuth flow) |
| `nebariapp.landingPage.enabled` | `false` | Add JupyterHub to the Nebari home page tile grid |

:::warning[`enforceAtGateway: false` is intentional]

Default values disable gateway-level OIDC enforcement
(`enforceAtGateway: false`) because JupyterHub is its own OAuth client
via `KeyCloakOAuthenticator` — running Envoy's OIDC filter on top adds
nothing and its cookie rotation lag stales out `auth_state` for
`/services/japps/*` paths. Leave it `false` unless you are sure you
want Envoy-level OIDC.

:::

### Explicit routing rules

`nebariapp.routing.routes` is unset by default — the chart's
`templates/nebariapp.yaml` only emits a `routing:` block when this
value is set, so the rendered NebariApp CR ships without explicit
routes unless you provide them. Whether that's enough depends on
how the nebari-operator handles a NebariApp with no routes; in some
deployments, the hostname returns 404 even when `RoutingReady: True`.

If you hit that, set an explicit catch-all route:

```yaml
nebariapp:
  enabled: true
  hostname: jupyter.your-cluster.example.com
  routing:
    routes:
      - pathPrefix: /
```

`pathPrefix: /` matches every URL under the hostname. Add more
specific routes ahead of it if you need to split traffic to other
services (rare for this pack).

## Profiles (resource sizing)

The chart ships two profiles in `jupyterhub.custom.profiles`:

| Slug | Default | Resources | Use case |
|---|---|---|---|
| `small-instance` | yes | 1 CPU / 2 GB RAM | interactive notebooks, light data exploration, teaching |
| `medium-instance` | no | 4 CPU / 8 GB RAM | pandas / scikit-learn on medium datasets |

Each entry maps directly to a KubeSpawner `profile_list` item; slugs
are derived from `display_name` via z2jh's slugify. Override the list
to add GPU profiles, custom images, or extra sizes — any KubeSpawner
trait (`cpu_limit`, `mem_limit`, `node_selector`, `image`,
`extra_resource_limits`, …) is accepted in `kubespawner_override`.

Set `jupyterhub.custom.profiles: []` to disable the profile selector
and fall back to single-instance mode.

### Adding a GPU profile

`config/jupyterhub/01-spawner.py` (the spawner config the chart
mounts into the hub) documents that `kubespawner_override` accepts
any KubeSpawner trait, calling out `node_selector`, `image`, and
`extra_resource_limits` for GPU specifically. The example below adds
an entry using only those three knobs:

```yaml
jupyterhub:
  custom:
    profiles:
      # ... keep the shipped small/medium entries above ...
      - slug: gpu
        display_name: "GPU Instance"
        description: "GPU-equipped pod for accelerated workloads."
        kubespawner_override:
          # Use whichever image has your CUDA stack baked in — re-use the
          # pack's JupyterLab image if it already has what you need.
          image: quay.io/nebari/nebari-data-science-pack-jupyterlab:<your-tag>
          cpu_limit: 8
          cpu_guarantee: 4
          mem_limit: "32G"
          mem_guarantee: "16G"
          # Target a node group with GPUs attached. Substitute the label
          # your cluster uses for node groups (e.g. cloud-provider-specific
          # nodepool labels, or your own).
          node_selector:
            <your-node-group-label>: <your-gpu-group-value>
          extra_resource_limits:
            nvidia.com/gpu: "1"
```

The pack does not pick a node-group label or runtime class for you —
those are cluster-specific. The shape of `node_selector` and
`extra_resource_limits` is whatever KubeSpawner accepts, since the
chart threads `kubespawner_override` through verbatim. For
GPU-scheduling specifics (the `nvidia.com/gpu` resource name, runtime
classes, device plugins), follow your cluster's GPU documentation;
the chart's only contribution is the profile plumbing.

Remember the triple-tag rule in the warning above if you keep the
inner `profile_options` block.

:::warning[Bump all three image tags together]

z2jh's `values.yaml` cannot reference other values, so the JupyterLab
image tag appears in three places per profile: the outer
`kubespawner_override.image`, the inner
`profile_options.image.choices.default.kubespawner_override.image`,
and its `display_name`. The repo ships
[`scripts/bump_image_tags.py`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/scripts/bump_image_tags.py)
which syncs all three. When overriding profiles in your own values
file, mirror the same triple.

:::

## Shared storage {#shared-storage}

Per-group `/shared/<group>` directories in every user pod, backed by a
`ReadWriteMany` PVC. On NIC-managed clusters the RWX class is
[Longhorn](https://longhorn.io/):

```yaml
sharedStorage:
  enabled: true
  storageClass: longhorn
  size: 100Gi
```

For clusters where NIC has not wired up an RWX class (local dev,
current GCP / Azure paths), the chart ships a transitional in-cluster
NFS server mode:

```yaml
sharedStorage:
  enabled: true
  nfsServer:
    enabled: true
    storageClass: ""   # default RWO StorageClass
    installClient: true  # add nfs-common DaemonSet for k3s / minimal nodes
```

The NFS server uses a `quay.io/nebari/volume-nfs` workaround image
(exact tag pinned in
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
under `sharedStorage.nfsServer.image.tag`) and is tracked for removal
in [issue #29](https://github.com/nebari-dev/nebari-data-science-pack/issues/29).
Prefer a native RWX class wherever possible.

:::warning[`shared-storage-enabled` must match]

`sharedStorage.enabled` and `jupyterhub.custom.shared-storage-enabled`
must match exactly — `helm template` fails the install if they
diverge. Same applies to `sharedStorage.groups` /
`jupyterhub.custom.shared-storage-groups` and
`sharedStorage.mountPathPrefix` /
`jupyterhub.custom.shared-storage-mount-prefix`.

:::

## Keycloak OAuth (production)

The default `dummy` authenticator is for local dev. For production,
switch JupyterHub to `GenericOAuthenticator` against Keycloak — when
the nebari-operator provisions the OIDC client (`provisionClient:
true`), the client-id, client-secret, and issuer-url are mounted into
the hub pod at `/etc/oauth/` and as `JUPYTERHUB_OIDC_CLIENT_SECRET`
env var. The `config/jupyterhub/00-gateway-auth.py` hub config file
picks them up automatically.

For manual Keycloak wiring (BYO-Keycloak deployments), see the
commented example block at the bottom of
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
under `jupyterhub.hub.config`.

## Keycloak RBAC bootstrap {#keycloak-rbac-bootstrap}

The chart includes a one-shot post-install Job
(`rbac.bootstrap.enabled: true`, on by default) that:

1. Adds the `oidc-group-membership-mapper` to the `groups` client
   scope — fixes the missing-mapper bug that surfaces as an empty
   `groups` claim on tokens.
2. Creates the `allow-group-directory-creation-role` client role on
   the hub OIDC client (so the spawner can role-gate shared-mount
   creation).
3. Grants `realm-management.{view-clients,view-groups,view-realm}` to
   the hub client's service account.
4. Assigns the shared-mount role to the KC groups in
   `rbac.bootstrap.sharedMountGroups`.

The Job reads the Keycloak admin password from a Secret (defaults to
`keycloak-admin-credentials` in the `keycloak` namespace — the
[bitnami/keycloakx](https://github.com/bitnami/charts/tree/main/bitnami/keycloak)
chart's layout). Set `rbac.bootstrap.enabled: false` on non-Nebari
clusters or when bringing your own Keycloak.

If the Job fails to authenticate, see
[Troubleshoot → Keycloak RBAC Job fails](./troubleshoot#keycloak-rbac-job-login-failed).

## Nebi integration

When the [nebi-pack](https://github.com/nebari-dev/nebari-nebi-pack) is
also deployed, set `nebi.remoteURL` and the JupyterLab pods
auto-connect to the Nebi team server using the user's Keycloak
`IdToken` cookie:

```yaml
nebi:
  image:
    repository: quay.io/nebari/nebi
    tag: <your-nebi-image-tag>   # pin to a tested sha — see values.yaml for the chart default
  remoteURL: https://nebi.your-cluster.example.com
  internalURL: http://nebi-pack-nebari-nebi-pack.nebi.svc.cluster.local
  namespace: nebi
  port: 8460
```

An init container copies the `nebi` binary from `nebi.image` into each
JupyterLab pod at spawn time, so the version is controlled at deploy
time rather than baked into the JupyterLab image. Leaving `remoteURL`
empty disables the Nebi auto-connect path entirely.

## MLflow integration

This pack does not deploy MLflow itself. The recommended path is to
install the [nebari-mlflow-pack](https://github.com/nebari-dev/nebari-mlflow-pack)
alongside it — that pack deploys MLflow with Keycloak auth, a
PostgreSQL backend, and automatic TLS, and its README documents the
exact wiring needed on the data-science side.

The integration is a two-piece change to the data-science-pack
values: an env var so the MLflow Python client knows where to push
runs, and a NetworkPolicy egress rule so user pods can actually reach
the MLflow namespace.

The verified pattern (lifted directly from the
[nebari-mlflow-pack README](https://github.com/nebari-dev/nebari-mlflow-pack/blob/main/README.md#connecting-jupyterhub)):

```yaml
jupyterhub:
  singleuser:
    extraEnv:
      MLFLOW_TRACKING_URI: "http://mlflow-pack.mlflow.svc.cluster.local:80"
    networkPolicy:
      egress:
        - ports:
            - port: 5000
              protocol: TCP
          to:
            - namespaceSelector:
                matchLabels:
                  kubernetes.io/metadata.name: mlflow
```

`MLFLOW_TRACKING_URI` flows through the pack's spawner
(`config/jupyterhub/01-spawner.py` reads `singleuser.extraEnv` and
attaches it to every user pod). Existing JupyterLab sessions must be
restarted (stop / start from the hub control panel) to pick up the
new env var and NetworkPolicy.

:::warning[Egress port 5000, not 80]

The egress rule targets pod port `5000` even though the Service is on
`80`. NetworkPolicy operates at the pod IP level, not the ClusterIP
service level (which maps `80` → `5000`). Quoting the
[nebari-mlflow-pack README](https://github.com/nebari-dev/nebari-mlflow-pack/blob/main/README.md#connecting-jupyterhub)
directly. If users see `Connection refused` from MLflow client calls,
this is the first thing to check.

:::

For anything outside the JupyterHub-side wiring — MLflow Helm values,
PostgreSQL backend, Keycloak client config, allowed-hosts — see the
[nebari-mlflow-pack docs](https://github.com/nebari-dev/nebari-mlflow-pack)
directly; it's a separate chart with its own configuration surface.

## See also

- [Deploy the pack](./deploy) — install paths and verification.
- [`values.yaml` reference](../references/values) — every chart value
  with its type, default, and description.
- [Troubleshoot](./troubleshoot) — recovery steps when a configuration
  change doesn't behave as expected.
