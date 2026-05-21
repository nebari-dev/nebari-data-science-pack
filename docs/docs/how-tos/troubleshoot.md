---
title: Troubleshoot
description: First-aid guide for the most common failures — login redirect loops, spawner timeouts, missing shared directories, NebariApp not Ready, jhub-apps registration errors.
sidebar_position: 2
---

# Troubleshoot

Quick index of the failure modes that come up most often. Each entry
links to the deeper write-up where the recovery steps live. Start
here, narrow to the right page, follow the steps.

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

- **Hub pod `Pending` / `CrashLoopBackOff`** → operator or chart layer.
  See [Deploy → Operator troubleshooting](../get-started/deploy#operator-troubleshooting).
- **Hub pod `Running` but spawn fails** → spawner layer. See
  [Spawner timeout](#spawner-times-out-during-startup) below.
- **Login redirect loops or `400 OAuth state mismatch`** → Keycloak
  client wiring. See [Login redirects in a loop](#login-redirects-in-a-loop).
- **NebariApp not Ready** → routing layer. See
  [NebariApp not reaching Ready](#nebariapp-not-reaching-ready).

## End-user failures

### Login redirects in a loop

After Keycloak login you bounce back to the login page, or get
`400 OAuth state mismatch`. Cause: the hub OAuth client's `rootUrl` /
`baseUrl` aren't set in Keycloak, so KC-initiated SSO flows skip
`/hub/oauth_login` and the `oauthenticator-state` cookie is never set.

→ Full recovery steps:
[Deploy → `400 OAuth state mismatch` after Keycloak login](../get-started/deploy#400-oauth-state-mismatch-after-keycloak-login).

### Spawner times out during startup

Progress page shows "Starting…" for over 2 minutes then errors out.
Common causes: cold node + large image pull, no matching node for the
profile's resource request, per-user home PVC fails to bind,
`ImagePullBackOff` on a wrong image tag.

→ Full recovery steps:
[Use the pack → Spawner times out during startup](./use#spawner-times-out-during-startup).

### `/shared/<group>` directories empty {#shared-directories-empty}

`ls /shared` returns nothing despite being in multiple Keycloak groups.
When RBAC is enabled, the spawner only mounts groups that hold the
`allow-group-directory-creation-role` shared-mount role. New groups
need to be added to `rbac.bootstrap.sharedMountGroups` and the Job
re-run.

→ Full recovery steps:
[Use the pack → /shared empty](./use#sharedgroup-directories-empty) →
[Deploy → /shared empty](../get-started/deploy#sharedgroup-empty-inside-user-pods).

### jhub-apps app stuck in `Failed`

`Create App` returns successfully but the app status flips to `Failed`.
Most often: an `ImportError` because the app's framework or model
dependency isn't in the JupyterLab image. Click the app in the
launcher to see logs.

→ Full recovery steps:
[Use the pack → jhub-apps app stuck in `Failed`](./use#jhub-apps-app-stuck-in-failed).

## Operator failures

### Hub falls back to `dummy` auth despite `nebariapp.auth.enabled`

You configured Keycloak OAuth in your deployer values but every user
lands on a username / password form. Cause: z2jh treats
`hub.extraVolumes` / `hub.extraVolumeMounts` as **replace-not-merge**
lists. If your deployer values set either, the chart's `custom-config`
and `oauth-client` mounts are gone — `jupyterhub_config.d/` is empty
and `/etc/oauth/` is unmounted, so the hub silently falls back to
`dummy`.

→ Full recovery steps:
[Deploy → Hub falls back to `dummy` auth despite `nebariapp.auth.enabled`](../get-started/deploy#hub-falls-back-to-dummy-auth-despite-nebariappauthenabled).

### NebariApp not reaching Ready

Most common cause: the namespace doesn't carry the
`nebari.dev/managed: "true"` label, so the nebari-operator silently
ignores NebariApp resources in it.

→ Full recovery steps:
[Deploy → NebariApp stuck with `RoutingReady: False`](../get-started/deploy#nebariapp-stuck-with-routingready-false).

### Keycloak RBAC Job fails with `kcadm.sh: login failed`

The bootstrap Job can't read the admin password from
`rbac.bootstrap.kcAdminCredentialSecret`. Defaults match
bitnami/keycloakx (`keycloak-admin-credentials` in the `keycloak`
namespace); other layouts need an override or
`rbac.bootstrap.enabled: false` to opt out.

→ Full recovery steps:
[Deploy → Keycloak RBAC Job fails with `kcadm.sh: login failed`](../get-started/deploy#keycloak-rbac-job-fails-with-kcadmsh-login-failed).

### `shared-storage-enabled` validation error on `helm template`

`sharedStorage.enabled` and `jupyterhub.custom.shared-storage-enabled`
diverge. The chart's `validateSharedStorage` helper fails the install
to stop the divergence reaching production (where the spawner and the
chart would disagree about whether to mount).

Set both to the same value (or set
`jupyterhub.custom.shared-storage-enabled` to match
`sharedStorage.enabled`). Same applies to `groups` and
`mountPathPrefix`. See the `sharedStorage` block in
[`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml).

## Still stuck?

- Compare `kubectl describe nebariapp -n data-science` against the
  [Architecture page](../references/architecture) to see which
  condition is failing.
- Open an issue at
  [nebari-data-science-pack/issues](https://github.com/nebari-dev/nebari-data-science-pack/issues)
  with the output of the three [First checks](#first-checks) commands
  and the last 200 lines of `kubectl logs` for the failing pod.
- For JupyterHub-specific behaviour, the upstream
  [Zero to JupyterHub troubleshooting](https://z2jh.jupyter.org/en/stable/administrator/troubleshooting.html)
  page covers spawner, proxy, and PVC failures in more depth.
