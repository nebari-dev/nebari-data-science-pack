---
title: Troubleshoot
description: Recovery steps for the failures operators and end users hit most often — login redirect loops, spawner timeouts, empty shared directories, NebariApp not Ready, jhub-apps registration errors, Keycloak bootstrap failures.
sidebar_position: 4
---

# Troubleshoot

Symptom-first index of the failures that come up most often, with the
recovery steps for each. End-user-visible failures are at the top;
operator-side failures (NebariApp, Keycloak, shared-storage validation)
follow.

## When in doubt

1. Refresh the page and try again — transient pod or network blips
   resolve on retry.
2. Note the exact error string, the time it happened, and what was in
   progress when it happened.
3. If you're an operator, run the [first checks](#first-checks) below.
   If you're a notebook user, hand the error string to your operator.

## First checks

If you're not sure what's broken, run these three commands and read the
output before diving into anything else:

```bash
# Are the hub and proxy up?
kubectl get pods -n data-science

# Are the services reachable?
kubectl get svc -n data-science

# If NebariApp is involved, is it Ready?
kubectl get nebariapp -n data-science
```

The output tells you which layer to focus on:

- **Hub pod `Pending` / `CrashLoopBackOff`** → operator/chart layer.
  See [NebariApp not reaching Ready](#nebariapp-not-reaching-ready)
  and [Keycloak RBAC Job login failed](#keycloak-rbac-job-login-failed)
  below.
- **Hub pod `Running` but spawn fails** → spawner layer. See
  [Spawner times out](#spawner-times-out-during-startup).
- **Login redirect loops or `400 OAuth state mismatch`** → Keycloak
  client wiring. See [Login redirects in a loop](#login-redirects-in-a-loop).

## End-user-visible failures

### Login redirects in a loop

After Keycloak login you bounce back to the login page, or get
`400 OAuth state mismatch`. Cause: the hub OAuth client's `rootUrl` /
`baseUrl` aren't set in Keycloak, so KC-initiated SSO flows skip
`/hub/oauth_login` and the `oauthenticator-state` cookie is never set.

**Fix (operator):** the bootstrap Job patches `rootUrl` / `baseUrl` /
`initiate.login.uri` from `rbac.bootstrap.hubExternalUrl` (or derives
from `https://{nebariapp.hostname}` when empty). Re-run the Job after
setting `rbac.bootstrap.hubExternalUrl` to the hub's external origin
explicitly.

### Spawner times out during startup

Progress page shows "Starting…" for over 2 minutes then errors out.

Most often:

- **Cold node + large image pull** — first spawn on a fresh node pulls
  the JupyterLab image (~3 GB). Subsequent spawns are fast.
- **No matching node** — the profile's `node_selector` or resource
  request doesn't match any node. End user: try a smaller profile.
  Operator: check `kubectl describe pod jupyter-<user>` for the
  scheduler's reason.
- **Per-user home PVC fails to bind** — usually a StorageClass issue;
  operator-side. `kubectl describe pvc` on the user's PVC names the
  failing provisioner.
- **`ImagePullBackOff`** — the JupyterLab image tag is wrong or has
  been deleted from the registry. Operator: bump the tag (see
  `scripts/bump_image_tags.py`).

### `/shared/<group>` directories empty {#shared-directories-empty}

`ls /shared` returns nothing despite being in multiple Keycloak groups.

When `rbac.bootstrap.enabled: true` and `hub.extraEnv.KC_REALM_API_URL`
is set, the spawner only mounts groups that hold the
`allow-group-directory-creation-role` shared-mount role. New groups
need to be added to `rbac.bootstrap.sharedMountGroups` and the Job
re-run.

**Fix (operator):**

```yaml
rbac:
  bootstrap:
    sharedMountGroups: [/admin, /developer, /<new-group>]
```

Then `helm upgrade` to re-run the Job. The Job is idempotent — repeat
runs are safe.

### jhub-apps app stuck in `Failed`

`Create App` returns successfully but the app status flips to
`Failed`. Click the app in the launcher to see logs. Most common
patterns:

- **`ImportError`** — the app uses a package that's not in the
  JupyterLab image. The package needs to be installed (in the user's
  home conda env, or — for shared use — baked into the JupyterLab
  image by the operator).
- **`Address already in use`** — happens when the same script is
  started twice in the same pod from a terminal. Stop the jhub-apps
  app from the launcher and recreate.
- **Hangs at "Pending"** — the app pod can't get scheduled; same
  causes as a spawner timeout.

## Operator-side failures

### Hub falls back to `dummy` auth despite `nebariapp.auth.enabled`

Configured Keycloak OAuth in deployer values but every user lands on
a username / password form. Cause: z2jh treats `hub.extraVolumes` /
`hub.extraVolumeMounts` as **replace-not-merge** lists. If the
deployer values set either, the chart's `custom-config` and
`oauth-client` mounts are gone — `jupyterhub_config.d/` is empty and
`/etc/oauth/` is unmounted, so the hub silently falls back to `dummy`.

**Fix:** re-include the `custom-config` and `oauth-client` entries
from the chart's default
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
in any deployer override of those keys.

### NebariApp not reaching Ready {#nebariapp-not-reaching-ready}

Most common cause: the namespace doesn't carry the
`nebari.dev/managed: "true"` label, so the nebari-operator silently
ignores NebariApp resources in it.

Check:

```bash
kubectl get namespace data-science --show-labels | grep nebari.dev/managed
```

Add the label (operators usually do this via ArgoCD's
`managedNamespaceMetadata` block, but for an existing namespace):

```bash
kubectl label namespace data-science nebari.dev/managed=true
```

### Hostname returns 404 even with `RoutingReady: True`

`kubectl get nebariapp` shows `RoutingReady: True` but the hub
hostname returns 404 (or the wrong upstream's content). The chart's
`templates/nebariapp.yaml` only emits a `routing:` block when
`nebariapp.routing` is set; if it's left unset, the rendered
NebariApp CR has no routes and the resulting HTTPRoute behaviour
depends on what the nebari-operator does when given no routes —
which has been observed to leave the hostname unrouted in some
deployments.

**Fix:** set an explicit catch-all route in the chart values:

```yaml
nebariapp:
  routing:
    routes:
      - pathPrefix: /
```

See [Configuration guide → Explicit routing rules](./configuration_guide#explicit-routing-rules).

### Keycloak RBAC Job fails with `kcadm.sh: login failed` {#keycloak-rbac-job-login-failed}

The bootstrap Job can't read the admin password from
`rbac.bootstrap.kcAdminCredentialSecret`. Defaults match
bitnami/keycloakx (`keycloak-admin-credentials` in the `keycloak`
namespace); other layouts need an override:

```yaml
rbac:
  bootstrap:
    namespace: <your-keycloak-ns>
    kcAdminCredentialSecret: <your-secret-name>
    kcAdminCredentialSecretKey: <key-within-the-secret>
```

To opt out entirely on local-dev / BYO-Keycloak clusters:

```yaml
rbac:
  bootstrap:
    enabled: false
```

### `shared-storage-enabled` validation error on `helm template`

`sharedStorage.enabled` and `jupyterhub.custom.shared-storage-enabled`
diverge. The chart's `validateSharedStorage` helper fails the install
to stop the divergence reaching production (where the spawner and the
chart would disagree about whether to mount).

Set both to the same value. Same applies to `groups` and
`mountPathPrefix`. See the `sharedStorage` block in the
[Configuration guide](./configuration_guide#shared-storage) or the raw
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml).

## Still stuck?

- Compare `kubectl describe nebariapp -n data-science` against the
  [Architecture page](./architecture) to see which condition is
  failing.
- For JupyterHub-specific behavior, the upstream
  [Zero to JupyterHub troubleshooting](https://z2jh.jupyter.org/en/stable/administrator/troubleshooting.html)
  page covers spawner, proxy, and PVC failures in more depth.
- For "is this expected?" or open-ended questions, start a thread on
  [GitHub Discussions](https://github.com/nebari-dev/nebari-data-science-pack/discussions).
- For confirmed bugs, open an issue at
  [nebari-data-science-pack/issues](https://github.com/nebari-dev/nebari-data-science-pack/issues)
  with the output of [First checks](#first-checks) and the last 200
  lines of `kubectl logs` for the failing pod.
