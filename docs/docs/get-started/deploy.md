---
title: Deploy the pack
description: Install the Nebari Data Science Pack on a standalone cluster or via ArgoCD on Nebari, then configure NebariApp routing, Keycloak OIDC, profiles, and shared storage.
sidebar_position: 2
---

# Deploy the pack

This guide is for **operators** installing the pack on a Kubernetes
cluster. End users connecting to an already-deployed cluster should read
[Use the pack from a notebook](../how-tos/use_pack_from_notebook) instead.

:::note[Defaults reflect chart v0.1.0-alpha.13]

Image tags, subchart versions, and other defaults cited below match
[`Chart.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/Chart.yaml)
and [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
on `main`. Check the repo for the latest pinned versions before copying
examples verbatim.

:::

The pack deploys:

- The **JupyterHub** subchart ([z2jh](https://z2jh.jupyter.org/)) — exact
  version pinned in [`Chart.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/Chart.yaml).
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

| Requirement | Details |
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
          routing:
            routes:
              # Explicit catch-all route. Some nebari-operator builds
              # don't synthesize a default route from `service:` alone;
              # if you skip this and see the hostname returning 404 with
              # `RoutingReady: True`, it's almost always this.
              - pathPrefix: /
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

Configuring the chart — NebariApp / external access, profiles, shared
storage, Keycloak OAuth, Keycloak RBAC bootstrap, Nebi integration —
lives on its own page so the install flow stays focused. See
**[Configuration guide](./configuration_guide)**.

For the exhaustive list of every chart value with its type and
default, see [Reference → `values.yaml` reference](../references/values).

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

Recovery steps for the failures operators hit most often — auth falling
back to `dummy`, NebariApp stuck on `RoutingReady`, Keycloak bootstrap
auth errors, `shared-storage-enabled` validation, `400 OAuth state
mismatch` — live on the [Troubleshoot](./troubleshoot) page.

## Next steps

- **End users** → [Use the pack from a notebook](../how-tos/use_pack_from_notebook) — start
  a server, pick a profile, deploy apps with jhub-apps.
- **Full chart reference** → [`values.yaml` reference](../references/values) —
  every option with type, default, and description.
- **How it fits together** → [Architecture](./architecture) —
  the Kubernetes resources the chart creates and how they interact.
- **Upstream docs** →
  [Zero to JupyterHub](https://z2jh.jupyter.org/),
  [jhub-apps](https://jhub-apps.nebari.dev/).
