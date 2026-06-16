+++
title = "Configuration"
weight = 1
description = "The chart's configuration values, from the single required field to the full set."
+++

The chart aims to ship sensible defaults so a fresh deploy needs only **one**
field: `keycloak.hostname`. Everything else is derived from it by subdomain
convention, and any field can be overridden explicitly.

See [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
for the authoritative list and inline documentation.

## Minimal deploy

```yaml
keycloak:
  hostname: keycloak.example.com   # drives derivation of hub and nebi URLs
```

From `keycloak.hostname` the chart derives the hub and nebi hostnames by
subdomain convention:

| Service | Derived from `keycloak.example.com` |
|---------|-------------------------------------|
| Hub | `hub.example.com` |
| Nebi | `nebi.example.com` |

Override `nebariapp.hostname` and `nebi.remoteURL` to break the convention.

## Top-level sections

| Key | Purpose |
|-----|---------|
| `keycloak` | External Keycloak FQDN, realm, and in-cluster service host. |
| `subdomains` | Subdomain labels used to derive hub and nebi hostnames. |
| `nebariapp` | NebariApp CRD: gateway routing and Keycloak OAuth. |
| `singleuser` | User pod settings, including the network policy to the gateway. |
| `singleuserCuller` | Idle culling for kernels, terminals, and servers inside user pods. |
| `sharedStorage` | Per-group shared directories. See [Shared Storage](/docs/shared-storage/). |
| `nebi` | Nebi companion service integration. |
| `rbac` | Keycloak role and group bootstrap. |
| `jupyterhub` | Passed straight through to the upstream JupyterHub chart. |

## Authentication

The default dummy authenticator accepts any username and password and is meant
for local development. For production, the `nebariapp.auth` block provisions an
OAuth client in Keycloak:

```yaml
nebariapp:
  auth:
    enabled: true
    provider: keycloak
    provisionClient: true
    redirectURI: /hub/oauth_callback
    scopes:
      - openid
      - profile
      - email
      - groups
```

## Idle culling

Idle culling inside each user pod is separate from the hub-level culler and runs
even when browser tabs are left open:

```yaml
singleuserCuller:
  kernel:
    cullConnected: true     # cull kernels even with open browser connections
    cullIdleTimeout: 900    # seconds before an idle kernel is culled
    cullInterval: 300       # how often to check for idle kernels
    cullBusy: false         # do not cull kernels that are running code
```

## Passing through to JupyterHub

The chart wraps the [JupyterHub Helm chart](https://z2jh.jupyter.org/). Anything
under `jupyterhub.*` is forwarded to the subchart unchanged, so you can set any
upstream value alongside the pack's own configuration.

{{< callout type="note" title="Image tags" >}}
Image tags for the hub, singleuser, and nebi images are pinned per chart release
by CI. Override them to test a build or to roll a version forward.
{{< /callout >}}
