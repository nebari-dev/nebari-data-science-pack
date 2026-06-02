---
title: values.yaml reference
description: Full reference for the chart's Helm values — every option, its type, default, and a short description.
sidebar_position: 1
---

# `values.yaml` reference

This page documents every option exposed by the chart. Source of truth
is [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
in the repo — the tables below mirror that file, grouped for readability.

:::note[Defaults reflect chart v0.1.0-alpha.13]

Image tags, subchart versions, and other defaults below are accurate
for the chart version in
[`Chart.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/Chart.yaml)
at the time of writing. For the exact pinned values on `main`, always
check [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml).

:::

For example install invocations and an ArgoCD `Application` manifest,
see [Get started → Deploy the pack](../get-started/deploy).

## NebariApp integration

Creates a NebariApp CR that the nebari-operator picks up to provision
Envoy Gateway routing, TLS, and optional Keycloak OIDC. Skip the whole
block (`nebariapp.enabled: false`) on a standalone cluster.

| Value | Type | Default | Description |
|---|---|---|---|
| `nebariapp.enabled` | bool | `true` | Master switch — create the NebariApp resource. |
| `nebariapp.hostname` | string | — | Hostname for the hub. **Required when `nebariapp.enabled: true`.** |
| `nebariapp.service.name` | string | `proxy-public` | Service the NebariApp targets — the JupyterHub proxy. |
| `nebariapp.service.port` | int | `80` | Service port. |
| `nebariapp.routing.routes` | list | — | Explicit route rules (e.g. `[{pathPrefix: /}]`). Some nebari-operator builds need this set explicitly; if `RoutingReady: True` but the hostname returns 404, add a catch-all rule here. See [Configuration guide → Explicit routing rules](../get-started/configuration_guide#explicit-routing-rules). |
| `nebariapp.auth.enabled` | bool | `true` | Require Keycloak OIDC for external access. |
| `nebariapp.auth.provider` | enum | `keycloak` | OIDC provider name. |
| `nebariapp.auth.provisionClient` | bool | `true` | Have the nebari-operator create the Keycloak client automatically. |
| `nebariapp.auth.redirectURI` | string | `/hub/oauth_callback` | OAuth callback. Must be the hub's callback path, not Envoy's — JupyterHub does its own OAuth dance. |
| `nebariapp.auth.scopes` | list | `[openid, profile, email, groups]` | OIDC scopes requested. |
| `nebariapp.auth.enforceAtGateway` | bool | `false` | Run Envoy's OIDC filter at the gateway. Off because the hub owns the OAuth flow and Envoy's cookie rotation stales `auth_state` for `/services/japps/*` paths. |
| `nebariapp.auth.forwardAccessToken` | bool | `false` | Have Envoy forward the upstream Bearer token. Off — the hub persists tokens to `auth_state` itself. |
| `nebariapp.landingPage.enabled` | bool | `false` | Add the hub to the Nebari home page tile grid. Requires nebari-operator with `LandingPageConfig` support. |
| `nebariapp.landingPage.displayName` | string | `JupyterHub` | Title on the landing tile (max 64 chars). |
| `nebariapp.landingPage.description` | string | `Interactive Python notebooks for data science` | Tile description (max 256 chars). |
| `nebariapp.landingPage.icon` | URL | _(Jupyter logo)_ | Tile icon URL. |
| `nebariapp.landingPage.category` | string | `Data Science` | Section the tile groups under. |
| `nebariapp.landingPage.priority` | int | `1` | Sort order on the landing page (lower = earlier). |
| `nebariapp.landingPage.externalUrl` | string | — | Override the URL derived from `nebariapp.hostname`. |
| `nebariapp.landingPage.healthCheck.enabled` | bool | `true` | Periodic probe so the tile reflects hub availability. |
| `nebariapp.landingPage.healthCheck.path` | string | `/hub/api/health` | HTTP path probed. |
| `nebariapp.landingPage.healthCheck.intervalSeconds` | int | `30` | Probe interval (10–300). |
| `nebariapp.landingPage.healthCheck.timeoutSeconds` | int | `5` | Probe timeout (1–30). |

## Singleuser idle culler

Configures idle culling *inside each user pod* — separate from the
hub-level `jupyterhub.cull` block. Culls kernels and terminals even
when the browser tab is left open, matching classic Nebari defaults.

| Value | Type | Default | Description |
|---|---|---|---|
| `singleuserCuller.kernel.cullConnected` | bool | `true` | Cull kernels even with open browser connections. |
| `singleuserCuller.kernel.cullIdleTimeout` | int | `900` | Seconds before an idle kernel is culled (15 min). |
| `singleuserCuller.kernel.cullInterval` | int | `300` | How often to check for idle kernels (5 min). |
| `singleuserCuller.kernel.cullBusy` | bool | `false` | Cull kernels that are actively running code. |
| `singleuserCuller.terminal.cullInactiveTimeout` | int | `900` | Seconds before an idle terminal is culled (15 min). |
| `singleuserCuller.terminal.cullInterval` | int | `300` | How often to check for idle terminals (5 min). |
| `singleuserCuller.server.shutdownNoActivityTimeout` | int | `900` | Seconds after last kernel/terminal gone before the server self-terminates. |

## Shared storage

Per-group `/shared/<group>` directories in every user pod. Requires a
`ReadWriteMany` StorageClass.

| Value | Type | Default | Description |
|---|---|---|---|
| `sharedStorage.enabled` | bool | `false` | Master switch. **Must match `jupyterhub.custom.shared-storage-enabled`** — `helm template` fails on divergence. |
| `sharedStorage.storageClass` | string | `""` | RWX StorageClass for the PVC. Empty = cluster default (must support RWX). |
| `sharedStorage.size` | string | `10Gi` | PVC capacity. |
| `sharedStorage.accessModes` | list | `[ReadWriteMany]` | PVC access modes. |
| `sharedStorage.groups` | list | `[]` | Allowlist of group names to mount. Empty = all groups from the user's token. |
| `sharedStorage.mountPathPrefix` | string | `/shared` | Mount path prefix inside user pods. |
| `sharedStorage.nfsServer.enabled` | bool | `false` | Run a transitional in-cluster NFS server pod (`quay.io/nebari/volume-nfs`) that re-exports a RWO PVC as RWX. For clusters without a native RWX class. Tracked for removal in [#29](https://github.com/nebari-dev/nebari-data-science-pack/issues/29). |
| `sharedStorage.nfsServer.storageClass` | string | `""` | StorageClass for the NFS backend RWO PVC. |
| `sharedStorage.nfsServer.image.repository` | string | `quay.io/nebari/volume-nfs` | NFS server image. |
| `sharedStorage.nfsServer.image.tag` | string | _(pinned in `values.yaml`)_ | NFS server image tag (manifest-schema repack — see comment in `values.yaml`). |
| `sharedStorage.nfsServer.installClient` | bool | `false` | Deploy a DaemonSet that installs `nfs-common` on every node. Required on k3s / minimal OS nodes that ship without NFS client tools. |
| `sharedStorage.nfsServer.nodeSelector` | map | `{}` | Pin the NFS server pod to specific nodes (avoids slow RWO PVC reattachment on reschedule). |
| `sharedStorage.nfsServer.nodeAffinity` | map | `{}` | Full nodeAffinity spec (overrides `nodeSelector` if both set). |
| `sharedStorage.nfsServer.mountOptions` | list | `[]` | NFS PV mountOptions. Set to `["nfsvers=3"]` on overlayfs nodes (kind, k3d, some containerd setups) where the volume-nfs image's NFSv4 export is broken. |

## Nebi integration

Wire the hub up to the [Nebi](https://github.com/nebari-dev/nebari-nebi-pack)
team server so JupyterLab pods auto-connect using the user's Keycloak
token.

| Value | Type | Default | Description |
|---|---|---|---|
| `nebi.image.repository` | string | `quay.io/nebari/nebi` | Nebi binary image (init container source). |
| `nebi.image.tag` | string | `""` | **Required when `nebi.remoteURL` is set** — pin to a tested `sha-*` build from the [Nebi container registry](https://quay.io/repository/nebari/nebi?tab=tags). |
| `nebi.image.pullPolicy` | string | `IfNotPresent` | Pull policy for the Nebi init container. |
| `nebi.remoteURL` | string | `""` | URL of the remote Nebi server (e.g. `https://nebi.your-cluster.example.com`). Empty = Nebi integration disabled. |
| `nebi.internalURL` | string | `""` | Cluster-internal URL for hub → Nebi token exchange (e.g. `http://nebi-pack-nebari-nebi-pack.nebi.svc.cluster.local`). |
| `nebi.namespace` | string | `""` | Namespace where nebi-pack is deployed. Enables the hub → Nebi NetworkPolicy. |
| `nebi.port` | int | `8460` | Port the Nebi server listens on. |

## Keycloak RBAC bootstrap

One-shot post-install / post-upgrade Job that provisions the
group-membership mapper and the shared-mount client role on the hub
OIDC client. Idempotent.

| Value | Type | Default | Description |
|---|---|---|---|
| `rbac.bootstrap.enabled` | bool | `true` | Run the Job. Set `false` on local-dev / BYO-Keycloak clusters. |
| `rbac.bootstrap.namespace` | string | `keycloak` | Namespace the Job runs in (needs read access to the admin-credentials Secret). |
| `rbac.bootstrap.kcAdminCredentialSecret` | string | `keycloak-admin-credentials` | Secret holding the KC admin password (bitnami/keycloakx default). |
| `rbac.bootstrap.kcAdminCredentialSecretKey` | string | `admin-password` | Key within the Secret. |
| `rbac.bootstrap.realmName` | string | `nebari` | KC realm to bootstrap. |
| `rbac.bootstrap.hubClientId` | string | `""` | OIDC client ID for the hub. Empty = derived from `jupyterhub-<release>-<chart>` (nebari-operator convention). |
| `rbac.bootstrap.sharedMountRoleName` | string | `allow-group-directory-creation-role` | Name of the client role the Job creates. Must match `KC_SHARED_MOUNT_ROLE` on the hub Deployment. |
| `rbac.bootstrap.sharedMountGroups` | list | `[]` | KC group paths to assign the shared-mount role to (e.g. `[/admin, /developer]`). Must already exist in KC. |
| `rbac.bootstrap.hubExternalUrl` | string | `""` | External hub URL — sets `rootUrl` / `baseUrl` / `initiate.login.uri` on the hub OIDC client. Empty = derived from `https://{nebariapp.hostname}`. Skip the patch entirely by setting the string `"false"`. |
| `rbac.bootstrap.kcHost` | string | `http://keycloak-keycloakx-http.keycloak.svc.cluster.local:8080` | Keycloak server URL the Job talks to. |
| `rbac.bootstrap.image` | string | `python:3.12-slim` | Image that runs `files/keycloak_rbac_bootstrap.py` (stdlib only). |

## JupyterHub subchart overrides

Everything under `jupyterhub.*` is passed through to the
[Zero to JupyterHub](https://z2jh.jupyter.org/) subchart unchanged. The
table below covers only the values the pack overrides or that you'll
most often touch — for the full subchart reference, see
[z2jh values.yaml](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/blob/main/jupyterhub/values.yaml).

### Custom hub config (`jupyterhub.custom.*`)

Read by z2jh's `get_config("custom.<key>")` in the hub config files
(`config/jupyterhub/*.py`).

| Value | Type | Default | Description |
|---|---|---|---|
| `jupyterhub.custom.external-url` | string | `""` | Sets `JupyterHub.bind_url` so internal OAuth redirects use the real hostname instead of `0.0.0.0`. |
| `jupyterhub.custom.nebi-image` | string | `""` | Nebi init container image (must match `nebi.image.repository:tag`). |
| `jupyterhub.custom.nebi-image-pull-policy` | string | `IfNotPresent` | Pull policy for the Nebi init container. |
| `jupyterhub.custom.nebi-remote-url` | string | `""` | Must match `nebi.remoteURL`. |
| `jupyterhub.custom.nebi-internal-url` | string | `""` | Must match `nebi.internalURL`. |
| `jupyterhub.custom.keycloak-token-url` | string | `""` | KC token endpoint for hub → Nebi token exchange. |
| `jupyterhub.custom.nebi-client-id` | string | `""` | Nebi's KC OIDC client ID. |
| `jupyterhub.custom.jupyterhub-client-id` | string | `""` | Hub's KC OIDC client ID. |
| `jupyterhub.custom.profiles` | list | _(see [Profiles](#profiles))_ | KubeSpawner `profile_list` items. `[]` = single-instance mode. |
| `jupyterhub.custom.terminal-customization` | bool | `true` | Use the Starship prompt in JupyterLab terminals. |
| `jupyterhub.custom.shared-storage-enabled` | bool | `false` | **Must match `sharedStorage.enabled`**. |
| `jupyterhub.custom.shared-storage-groups` | list | `[]` | **Must match `sharedStorage.groups`**. |
| `jupyterhub.custom.shared-storage-mount-prefix` | string | `/shared` | **Must match `sharedStorage.mountPathPrefix`**. |
| `jupyterhub.custom.japps-config.hub_host` | string | `hub` | jhub-apps' `JAppsConfig.hub_host`. |
| `jupyterhub.custom.japps-config.service_workers` | int | `4` | jhub-apps service worker count. |

### Profiles

`jupyterhub.custom.profiles` is a list of KubeSpawner `profile_list`
items. Default entries:

| Slug | Default | CPU | Memory | Use case |
|---|---|---|---|---|
| `small-instance` | yes | 1 / 0.5 (limit / guarantee) | 2G / 1G | Interactive notebooks, light data exploration. |
| `medium-instance` | no | 4 / 2 | 8G / 4G | pandas / scikit-learn on medium datasets. |

Each entry maps directly to a KubeSpawner profile. Any KubeSpawner
trait (`cpu_limit`, `mem_limit`, `node_selector`, `image`,
`extra_resource_limits`, …) is accepted in `kubespawner_override`.

:::warning[Triple image-tag duplication]

z2jh's `values.yaml` cannot reference other values, so the JupyterLab
image tag appears in three places per profile: the outer
`kubespawner_override.image`, the inner
`profile_options.image.choices.default.kubespawner_override.image`,
and its `display_name`.
[`scripts/bump_image_tags.py`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/scripts/bump_image_tags.py)
keeps them in sync.

:::

### Hub container

| Value | Type | Default | Description |
|---|---|---|---|
| `jupyterhub.hub.image.name` | string | `quay.io/nebari/nebari-data-science-pack-jupyterhub` | Hub image. Custom Nebari image with jhub-apps + KeyCloakOAuthenticator pre-installed. |
| `jupyterhub.hub.image.tag` | string | _(pinned in `values.yaml`)_ | Hub image tag. Bump via `scripts/bump_image_tags.py`. |
| `jupyterhub.hub.config.JupyterHub.admin_access` | bool | `true` | Allow admins to access user servers. |
| `jupyterhub.hub.config.JupyterHub.authenticator_class` | string | `dummy` | Authenticator. `dummy` for local dev (any user/pass); `generic-oauth` for production Keycloak. |
| `jupyterhub.hub.extraVolumes` | list | _(custom-config + oauth-client)_ | **Replace-not-merge**: deployer overrides must re-include both entries or hub config and `/etc/oauth` disappear. |
| `jupyterhub.hub.extraVolumeMounts` | list | _(matching mounts)_ | Same merge caveat. |
| `jupyterhub.hub.extraEnv.JUPYTERHUB_OIDC_CLIENT_SECRET` | secretRef | _(operator-provisioned)_ | Read from the operator-created OIDC client Secret. Used by `02-jhub-apps.py` and `03-nebi-envs.py` for KC token exchange. |
| `jupyterhub.hub.service.extraPorts` | list | `[port: 10202]` | Adds the jhub-apps service port. |
| `jupyterhub.hub.networkPolicy.enabled` | bool | `true` | NetworkPolicy on the hub. |
| `jupyterhub.hub.networkPolicy.ingress` | list | `[port: 10202]` | Allow proxy → hub on the jhub-apps port. |

### Singleuser (JupyterLab) pod

| Value | Type | Default | Description |
|---|---|---|---|
| `jupyterhub.singleuser.image.name` | string | `quay.io/nebari/nebari-data-science-pack-jupyterlab` | JupyterLab image. |
| `jupyterhub.singleuser.image.tag` | string | _(pinned in `values.yaml`)_ | JupyterLab image tag. Must match the profile entries. |
| `jupyterhub.singleuser.defaultUrl` | string | `/lab` | Land users in JupyterLab (not classic notebook). |
| `jupyterhub.singleuser.extraEnv.JUPYTERHUB_SINGLEUSER_APP` | string | `jupyter_server.serverapp.ServerApp` | Required by jhub-apps. |
| `jupyterhub.singleuser.storage.type` | enum | `none` | **Required**: jhub-apps' `JHubSpawner` expects a list, but the subchart's dynamic storage emits a dict. The pack configures the home PVC in `01-spawner.py` instead. |

### Proxy

| Value | Type | Default | Description |
|---|---|---|---|
| `jupyterhub.proxy.service.type` | enum | `ClusterIP` | Proxy Service type. NebariApp handles external exposure. |
| `jupyterhub.proxy.chp.networkPolicy.egress` | list | `[port: 10202]` | Allow proxy → hub on the jhub-apps port. |

### Scheduling

| Value | Type | Default | Description |
|---|---|---|---|
| `jupyterhub.scheduling.userScheduler.enabled` | bool | `false` | z2jh's user scheduler. Disabled — the default Kubernetes scheduler handles user pod placement. |

### Hub-level idle culler

Separate from `singleuserCuller` above — this is JupyterHub's
[`jupyterhub-idle-culler`](https://github.com/jupyterhub/jupyterhub-idle-culler),
which culls **interactive notebook servers** (not jhub-apps).

| Value | Type | Default | Description |
|---|---|---|---|
| `jupyterhub.cull.enabled` | bool | `true` | Enable the hub-level culler. |
| `jupyterhub.cull.timeout` | int | `1800` | Seconds before an idle server is culled (30 min — matches classic Nebari). |
| `jupyterhub.cull.every` | int | `600` | Polling interval (10 min). |

## Chart metadata

| Value | Type | Default | Description |
|---|---|---|---|
| `apiVersion` | string | `v2` | Helm chart API version. |
| `name` | string | `nebari-data-science-pack` | Chart name. |
| `version` | string | _(see `Chart.yaml`)_ | Chart version. |
| `appVersion` | string | `1.0.0` | Pack app version. |
| `dependencies[0]` | — | `jupyterhub` _(version pinned in `Chart.yaml`)_ | Z2JH subchart dependency. |
