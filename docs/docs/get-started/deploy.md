---
title: Deploy the pack
description: Install the Nebari Data Science Pack on a standalone cluster or via ArgoCD on Nebari, then configure NebariApp routing, Keycloak OIDC, profiles, and shared storage.
sidebar_position: 2
---

# Deploy the pack

This guide is for **operators** installing the pack on a Kubernetes
cluster. End users connecting to an already-deployed cluster should read
[Use the pack from a notebook](../how-tos/use) instead.

The pack deploys:

- The **JupyterHub** subchart ([z2jh](https://z2jh.jupyter.org/) 4.3.2).
- A custom Nebari hub image with **jhub-apps** pre-installed and the hub
  config files (`00-gateway-auth.py`, `01-spawner.py`, `02-jhub-apps.py`,
  `03-nebi-envs.py`) mounted in.
- Optional **NebariApp** resources for routing, TLS, and Keycloak OIDC
  auth via Envoy Gateway and the nebari-operator (only when
  `nebariapp.enabled: true`).
- Optional **shared storage** — a `ReadWriteMany` PVC exposed as
  per-group `/shared/<group>` directories in user pods.
- An optional **Keycloak RBAC bootstrap Job** that provisions the
  `oidc-group-membership-mapper` and the shared-mount client role on the
  hub OIDC client (only when `rbac.bootstrap.enabled: true`).

## Prerequisites

| | |
|---|---|
| Kubernetes | 1.25+; [kind](https://kind.sigs.k8s.io/) / [k3d](https://k3d.io/) work for local dev |
| Tooling | [`kubectl`](https://kubernetes.io/docs/tasks/tools/), [Helm 3](https://helm.sh/docs/intro/install/) |
| For Nebari deployments | nebari-operator and Envoy Gateway already installed; an ArgoCD instance and a GitOps repo |
| For OIDC auth | Keycloak already deployed and reachable from the gateway |
| For shared storage | A `ReadWriteMany` StorageClass on the cluster (e.g. [Longhorn](https://longhorn.io/) on NIC-managed clusters), or use the transitional in-cluster NFS server fallback |

## Standalone install (no Nebari)

Use this path for local dev or clusters without nebari-operator. Skips the
NebariApp routing layer entirely and falls back to the `dummy`
authenticator so any username / password works.

### From the Helm repository

```bash
helm repo add nebari https://nebari-dev.github.io/nebari-data-science-pack
helm repo update
helm install data-science-pack nebari/nebari-data-science-pack \
  --create-namespace -n data-science --wait --timeout 5m
```

### From source

```bash
git clone https://github.com/nebari-dev/nebari-data-science-pack.git
cd nebari-data-science-pack
helm dependency update .
helm install data-science-pack . \
  --create-namespace -n data-science --wait --timeout 5m
```

After install, port-forward the JupyterHub proxy:

```bash
kubectl port-forward -n data-science svc/proxy-public 8000:80
```

Open `http://localhost:8000` and log in with any username / password —
the default `dummy` authenticator accepts anything.

### Local dev loop (Tilt + k3d)

The repo ships a Tiltfile and `ctlptl-config.yaml` for an end-to-end
local dev loop. Prerequisites:
[Docker](https://docs.docker.com/get-docker/),
[ctlptl](https://github.com/tilt-dev/ctlptl),
[Tilt](https://docs.tilt.dev/install.html).

```bash
make up          # k3d cluster + Tilt
# Tilt UI:      http://localhost:10350
# JupyterHub:   http://localhost:8000
make down        # tear down
```

## Nebari install (ArgoCD + GitOps)

The recommended production deployment. The chart creates a NebariApp
resource that the nebari-operator picks up to provision routing, TLS, and
Keycloak OIDC.

Drop the following at `apps/data-science-pack.yaml` in your GitOps repo:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: data-science-pack
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "7"
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/nebari-dev/nebari-data-science-pack.git
    targetRevision: main
    path: .
    helm:
      releaseName: data-science-pack
      values: |
        nebariapp:
          enabled: true
          hostname: jupyter.your-cluster.example.com
          auth:
            enabled: true
            provider: keycloak
            provisionClient: true
            # Hub does its own OAuth dance — see config/jupyterhub/00-gateway-auth.py
            redirectURI: /hub/oauth_callback
            enforceAtGateway: false
            forwardAccessToken: false
          landingPage:
            enabled: true
        sharedStorage:
          enabled: true
          storageClass: longhorn
          size: 100Gi
  destination:
    server: https://kubernetes.default.svc
    namespace: data-science
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    managedNamespaceMetadata:
      labels:
        nebari.dev/managed: "true"
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
      - SkipDryRunOnMissingResource=true
      - RespectIgnoreDifferences=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

:::warning[`nebari.dev/managed: "true"` is required]

The `managedNamespaceMetadata` block applies the `nebari.dev/managed`
label to the namespace. **Drop this and the nebari-operator will silently
ignore your NebariApp resource** — the hostname will resolve but return
404 or the wrong content, and `kubectl describe nebariapp` will show no
progress on conditions.

:::

:::warning[`enforceAtGateway: false` is intentional]

Default values disable gateway-level OIDC enforcement (`enforceAtGateway:
false`) because JupyterHub is its own OAuth client via
`KeyCloakOAuthenticator` — running Envoy's OIDC filter on top of that
adds nothing and its cookie rotation lag stales out `auth_state` for
`/services/japps/*` paths. Leave it `false` unless you are sure you want
Envoy-level OIDC.

:::

## Configuration

The full reference — every chart value with its type, default, and
description — lives at [Reference → `values.yaml` reference](../references/values).
The tables below cover the knobs you'll most often touch when installing.

### NebariApp / external access

| Value | Default | Description |
|---|---|---|
| `nebariapp.enabled` | `true` | Create the NebariApp resource for routing / TLS / auth |
| `nebariapp.hostname` | — | Hostname for the hub (required when `nebariapp.enabled`) |
| `nebariapp.service.name` | `proxy-public` | JupyterHub proxy service |
| `nebariapp.service.port` | `80` | Proxy service port |
| `nebariapp.auth.enabled` | `true` | Require Keycloak OIDC for external access |
| `nebariapp.auth.redirectURI` | `/hub/oauth_callback` | OAuth callback — must match the hub's, not Envoy's, callback path |
| `nebariapp.auth.enforceAtGateway` | `false` | Run Envoy's OIDC filter at the gateway (off by default — see warning above) |
| `nebariapp.auth.forwardAccessToken` | `false` | Have Envoy forward the upstream Bearer token (off — hub owns the OAuth flow) |
| `nebariapp.landingPage.enabled` | `false` | Add JupyterHub to the Nebari home page tile grid |

### Profiles (resource sizing)

The chart ships two profiles in `jupyterhub.custom.profiles`:

| Slug | Default | Resources | Use case |
|---|---|---|---|
| `small-instance` | yes | 1 CPU / 2 GB RAM | interactive notebooks, light data exploration, teaching |
| `medium-instance` | no | 4 CPU / 8 GB RAM | pandas / scikit-learn on medium datasets |

Each entry maps directly to a KubeSpawner `profile_list` item; slugs are
derived from `display_name` via z2jh's slugify. Override the list to add
GPU profiles, custom images, or extra sizes — any KubeSpawner trait
(`cpu_limit`, `mem_limit`, `node_selector`, `image`,
`extra_resource_limits`, …) is accepted in `kubespawner_override`.

Set `jupyterhub.custom.profiles: []` to disable the profile selector and
fall back to single-instance mode.

:::warning[Bump all three image tags together]

z2jh's `values.yaml` cannot reference other values, so the JupyterLab
image tag appears in three places per profile: the outer
`kubespawner_override.image`, the inner
`profile_options.image.choices.default.kubespawner_override.image`, and
its `display_name`. The repo ships
[`scripts/bump_image_tags.py`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/scripts/bump_image_tags.py)
which syncs all three. When overriding profiles in your own values
file, mirror the same triple.

:::

### Shared storage

Per-group `/shared/<group>` directories in every user pod, backed by a
`ReadWriteMany` PVC. On NIC-managed clusters the RWX class is
[Longhorn](https://longhorn.io/):

```yaml
sharedStorage:
  enabled: true
  storageClass: longhorn
  size: 100Gi
```

For clusters where NIC has not wired up an RWX class (local dev, current
GCP / Azure paths), the chart ships a transitional in-cluster NFS server
mode:

```yaml
sharedStorage:
  enabled: true
  nfsServer:
    enabled: true
    storageClass: ""   # default RWO StorageClass
    installClient: true  # add nfs-common DaemonSet for k3s / minimal nodes
```

The NFS server depends on the `quay.io/nebari/volume-nfs:0.8-repack`
workaround image and is tracked for removal in
[issue #29](https://github.com/nebari-dev/nebari-data-science-pack/issues/29).
Prefer a native RWX class wherever possible.

:::warning[`shared-storage-enabled` must match]

`sharedStorage.enabled` and `jupyterhub.custom.shared-storage-enabled`
must match exactly — `helm template` fails the install if they
diverge. Same applies to `sharedStorage.groups` /
`jupyterhub.custom.shared-storage-groups` and
`sharedStorage.mountPathPrefix` /
`jupyterhub.custom.shared-storage-mount-prefix`.

:::

### Keycloak OAuth (production)

The default `dummy` authenticator is for local dev. For production,
switch JupyterHub to `GenericOAuthenticator` against Keycloak — when the
nebari-operator provisions the OIDC client (`provisionClient: true`), the
client-id, client-secret, and issuer-url are mounted into the hub pod at
`/etc/oauth/` and as `JUPYTERHUB_OIDC_CLIENT_SECRET` env var. The
`config/jupyterhub/00-gateway-auth.py` hub config file picks them up
automatically.

For manual Keycloak wiring (BYO-Keycloak deployments), see the commented
example block at the bottom of
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
under `jupyterhub.hub.config`.

### Keycloak RBAC bootstrap

The chart includes a one-shot post-install Job
(`rbac.bootstrap.enabled: true`, on by default) that:

1. Adds the `oidc-group-membership-mapper` to the `groups` client scope —
   fixes the missing-mapper bug that surfaces as an empty `groups` claim
   on tokens.
2. Creates the `allow-group-directory-creation-role` client role on the
   hub OIDC client (so the spawner can role-gate shared-mount creation).
3. Grants `realm-management.{view-clients,view-groups,view-realm}` to the
   hub client's service account.
4. Assigns the shared-mount role to the KC groups in
   `rbac.bootstrap.sharedMountGroups`.

The Job reads the Keycloak admin password from a Secret (defaults to
`keycloak-admin-credentials` in the `keycloak` namespace — the
[bitnami/keycloakx](https://github.com/bitnami/charts/tree/main/bitnami/keycloak)
chart's layout). Set `rbac.bootstrap.enabled: false` on non-Nebari
clusters or when bringing your own Keycloak.

### Nebi integration

When the [nebi-pack](https://github.com/nebari-dev/nebari-nebi-pack) is
also deployed, set `nebi.remoteURL` and the JupyterLab pods auto-connect
to the Nebi team server using the user's Keycloak `IdToken` cookie:

```yaml
nebi:
  image:
    repository: quay.io/nebari/nebi
    tag: sha-a2c937a
  remoteURL: https://nebi.your-cluster.example.com
  internalURL: http://nebi-pack-nebari-nebi-pack.nebi.svc.cluster.local
  namespace: nebi
  port: 8460
```

An init container copies the `nebi` binary from `nebi.image` into each
JupyterLab pod at spawn time, so the version is controlled at deploy
time rather than baked into the JupyterLab image. Leaving `remoteURL`
empty disables the Nebi auto-connect path entirely.

## Verifying the deployment

After install (or ArgoCD sync), check the hub and the proxy are running:

```bash
kubectl get pods -n data-science
kubectl get svc -n data-science
```

Expected: a `hub-*` pod (`Running`, `1/1 Ready`), a `proxy-*` pod
(`Running`, `1/1 Ready`), and a `proxy-public` service of type
`ClusterIP`.

If `nebariapp.enabled`, check the NebariApp conditions:

```bash
kubectl get nebariapp -n data-science
kubectl describe nebariapp -n data-science
```

You want `RoutingReady`, `TLSReady`, and (when auth is on) `AuthReady`
all `True`.

## Operator troubleshooting

### Hub falls back to `dummy` auth despite `nebariapp.auth.enabled`

z2jh treats `hub.extraVolumes` and `hub.extraVolumeMounts` as **lists
that replace (not merge) on override**. If your deployment-specific
values file sets either, you must re-include the `custom-config` and
`oauth-client` entries from the chart's default
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
or the hub's `jupyterhub_config.d` ends up empty and `/etc/oauth/` is
never mounted.

### NebariApp stuck with `RoutingReady: False`

Most common cause: the namespace doesn't carry the
`nebari.dev/managed: "true"` label.

```bash
kubectl get namespace data-science --show-labels | grep nebari.dev/managed
```

If missing, add it (operators usually do this via the ArgoCD
`managedNamespaceMetadata` block, but for an existing namespace):

```bash
kubectl label namespace data-science nebari.dev/managed=true
```

### Keycloak RBAC Job fails with `kcadm.sh: login failed`

The Job reads the admin password from `rbac.bootstrap.kcAdminCredentialSecret`
in `rbac.bootstrap.namespace` (defaults: `keycloak-admin-credentials` in
the `keycloak` namespace, matching bitnami/keycloakx). For non-bitnami
layouts, override these to point at the right Secret + key.

To opt out entirely on local-dev / BYO-Keycloak clusters:

```yaml
rbac:
  bootstrap:
    enabled: false
```

### `400 OAuth state mismatch` after Keycloak login

JupyterHub fell into the OAuth callback without first hitting
`/hub/oauth_login`, so the `oauthenticator-state` cookie was never set.
Cause: the Keycloak client's `rootUrl` / `baseUrl` / `initiate.login.uri`
aren't set, so KC-initiated SSO flows (account console, third-party
launchers) redirect straight to `/hub/oauth_callback`.

The bootstrap Job patches these from `rbac.bootstrap.hubExternalUrl`
(or, if empty, derives from `https://{nebariapp.hostname}`). Re-run the
Job after correcting that value, or set `rbac.bootstrap.hubExternalUrl`
to your hub's external origin explicitly.

### `/shared/<group>` empty inside user pods

Check the `shared-storage-enabled` consistency invariant first:

```bash
helm template . -n data-science > /tmp/render.yaml
grep -E '^( |-) (shared-storage-enabled|sharedStorage:|enabled:)' /tmp/render.yaml
```

If both flags are `true` but the directories are empty, the spawner
falls back to mounting every group from the user's token. Confirm the
shared-mount role is assigned to the user's KC group (see
[Keycloak RBAC bootstrap](#keycloak-rbac-bootstrap) above) and that
`hub.extraEnv.KC_REALM_API_URL` is set in your deployer values — when
empty, RBAC is off and the spawner mounts everything.

## Next steps

- **End users** → [Use the pack from a notebook](../how-tos/use) — start
  a server, pick a profile, deploy apps with jhub-apps.
- **Full chart reference** → [`values.yaml` reference](../references/values) —
  every option with type, default, and description, sourced from
  [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml).
- **How it fits together** → [Architecture](../references/architecture) —
  the Kubernetes resources the chart creates and how they interact.
- **Upstream docs** →
  [Zero to JupyterHub](https://z2jh.jupyter.org/),
  [jhub-apps](https://jhub-apps.nebari.dev/).
