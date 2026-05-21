---
title: Use the pack from a notebook
description: Log in to JupyterHub, pick a profile, work with shared storage, and deploy apps through the jhub-apps launcher.
sidebar_position: 1
---

# Use the pack from a notebook

End-user guide for the Nebari Data Science Pack. This walks through
logging in, choosing a profile, working with `/shared/<group>`
directories, and deploying apps through jhub-apps.

The pack is administered separately — operators install the chart,
configure NebariApp routing, and pick the JupyterLab image. This guide
assumes that has already been done and the hub is healthy. For install
and operations, see [Get started → Deploy the pack](../get-started/deploy).

## Step 1 — Log in

Open the hub URL your operator gave you (`https://jupyter.<your-cluster>`
in production, or `http://localhost:8000` after a local
`kubectl port-forward svc/proxy-public 8000:80 -n data-science`).

Two authenticators are possible:

- **Production (Keycloak OIDC)** — the login page redirects you to
  Keycloak. Sign in with your Nebari credentials; you land back on the
  hub.
- **Local dev (`dummy` authenticator)** — the login page asks for a
  username and password directly. Any non-empty pair is accepted.

If the login page shows an OAuth error, jump to
[Troubleshooting](#troubleshooting).

## Step 2 — Pick a profile

Once logged in, the hub presents the profile selector with the choices
the chart ships:

| Profile | Resources | Use case |
|---|---|---|
| Small Instance (default) | 1 CPU / 2 GB RAM | Interactive notebooks, light data exploration, teaching. |
| Medium Instance | 4 CPU / 8 GB RAM | pandas / scikit-learn workloads on medium datasets. |

Pick one and click **Start**. Profiles map to KubeSpawner `profile_list`
entries — your operator may have added GPU or larger-memory profiles. The
selected profile sets the JupyterLab pod's CPU / memory limits and the
container image, but the rest of the environment (jhub-apps, shared
storage, Nebi connection) is the same across profiles.

The first spawn pulls the JupyterLab image (`quay.io/nebari/nebari-data-science-pack-jupyterlab`)
which can take a minute or two on a cold node. Subsequent spawns reuse
the cached image and start in 10–20 seconds.

If your spawn times out or hangs at "Starting", check
[Troubleshoot → Spawner timeout](./troubleshoot#spawner-times-out-during-startup).

## Step 3 — Work with shared storage

When the operator enables `sharedStorage`, each Keycloak group you
belong to becomes a directory under `/shared/<group>` in your user pod.
For example, a user in `/admin` and `/data-team` sees:

```bash
ls /shared
# admin  data-team
```

These directories are backed by a single `ReadWriteMany` PVC, so
changes made by one user are visible to every other member of the same
group in real time. Common patterns:

- **Shared datasets** — drop CSVs / parquet under
  `/shared/<group>/datasets/` so the whole team reads from one copy.
- **Shared notebooks** — `cp my-notebook.ipynb /shared/<group>/` to
  hand it off to a collaborator.
- **Shared conda envs** — write a `pixi.toml` under
  `/shared/<group>/envs/<env-name>/` and activate it from any user pod.

Your home directory (`/home/jovyan`) stays per-user — only `/shared`
is collaborative.

:::warning[Empty `/shared`]

If `/shared` is empty when you log in, RBAC may not have your group
mapped to the shared-mount role yet. Ask your operator to add your
KC group to `rbac.bootstrap.sharedMountGroups` and re-run the bootstrap
Job. See
[Troubleshoot → /shared empty](./troubleshoot#shared-directories-empty).

:::

## Step 4 — Deploy apps with jhub-apps

The pack ships with [jhub-apps](https://jhub-apps.nebari.dev/) — the
JupyterHub extension for deploying long-running data apps (Streamlit,
Panel, Voilà, Bokeh, …) on top of the hub.

Open the launcher (Hub control panel → **App Launcher**, or
`/services/japps/`). Click **Create App** and:

1. **Pick a framework** — Streamlit / Panel / Voilà / Bokeh / Gradio.
2. **Point at your code** — typically a script or notebook in your home
   directory or a shared mount (e.g. `/shared/data-team/dashboards/app.py`).
3. **Pick a server type** — same profile choices as a regular notebook.
4. **Set visibility** — public, your account only, or members of selected
   groups.
5. Click **Create** — jhub-apps registers the app with the hub and a
   dedicated pod is spawned to serve it.

Your app appears in the launcher with a status badge:

- **Running (green)** — reachable at the URL shown.
- **Stopped (gray)** — start it from the row's menu.
- **Failed (red)** — click the app to see logs; most failures are import
  errors. Hand the error to your operator if the missing package needs
  baking into the JupyterLab image.

The app keeps running after you close your browser — jhub-apps does not
stop apps when you sign out. The hub-level
[`jupyterhub-idle-culler`](https://github.com/jupyterhub/jupyterhub-idle-culler)
(configured under `jupyterhub.cull` by the chart) culls **interactive
notebook servers** that go idle for 30 minutes, but it does **not**
cull jhub-apps. Stop an app from the launcher when you're done.

The per-pod idle culler (`singleuserCuller` in the chart) culls **idle
kernels and terminals inside a running notebook pod** after 15 minutes,
even when the browser tab is open — so leave a long calculation
running explicitly via the kernel, not by typing a cell.

## Step 5 — Nebi integration (when enabled)

If the operator deployed the [nebi-pack](https://github.com/nebari-dev/nebari-nebi-pack)
alongside the data-science-pack and set `nebi.remoteURL`, your
JupyterLab pod auto-connects to the Nebi team server using your
Keycloak `IdToken` cookie. Look for the Nebi panel in the JupyterLab
sidebar — workspaces and environments published by your team are
listed there with no extra login.

When `nebi.remoteURL` is empty, the panel still renders but is local
only; ask your operator whether the cluster has a Nebi server.

## Accessing the hub from outside the cluster

In production the hub is reachable at `https://jupyter.<your-cluster>`
via Envoy Gateway, TLS-terminated, and OIDC-gated by Keycloak. The
first request returns a 302 to Keycloak; after login, a session cookie
is set and subsequent requests pass through.

If your operator did **not** enable `nebariapp.enabled`, the hub is
reachable only via `kubectl port-forward`:

```bash
kubectl port-forward -n data-science svc/proxy-public 8000:80
```

Open `http://localhost:8000`.

## Troubleshooting

### Login redirects in a loop

The hub OAuth client's `rootUrl` / `baseUrl` aren't set in Keycloak, so
the hub never sees the `oauthenticator-state` cookie that pairs the
login request with the callback.

Symptom: after Keycloak login you bounce back to the login page, or
get `400 OAuth state mismatch`.

Ask your operator to re-run the
[Keycloak RBAC bootstrap Job](../get-started/deploy#keycloak-rbac-bootstrap)
with the correct `rbac.bootstrap.hubExternalUrl`.

### Spawner times out during startup

The progress page shows "Starting…" for over 2 minutes, then errors
out.

Common causes:

- **Cold node + large image** — first spawn on a fresh node pulls the
  JupyterLab image (~3 GB). Wait it out the first time; subsequent
  spawns are fast.
- **No matching node** — the profile's `node_selector` or resource
  request doesn't match any node. Pick a smaller profile, or ask your
  operator.
- **PVC binding failure** — the per-user home PVC can't be bound.
  Usually a StorageClass issue; ask your operator.
- **`ImagePullBackOff`** — the JupyterLab image tag in the profile is
  wrong or has been deleted from the registry. Ask your operator to
  bump the tag (`scripts/bump_image_tags.py`).

### `/shared/<group>` directories empty

When `rbac.bootstrap` is enabled and `hub.extraEnv.KC_REALM_API_URL` is
set, the spawner only mounts groups that hold the
`allow-group-directory-creation-role` shared-mount role. New groups need
to be added to `rbac.bootstrap.sharedMountGroups` and the Job re-run.

Symptom: `ls /shared` returns nothing, even though you're in multiple
Keycloak groups.

Ask your operator. The full recovery steps live at
[Deploy → `/shared/<group>` empty inside user pods](../get-started/deploy#sharedgroup-empty-inside-user-pods).

### jhub-apps app stuck in `Failed`

Click the app in the launcher to see logs. Common patterns:

- **`ImportError`** — the app uses a package that's not in the
  JupyterLab image. Confirm the import works in a regular notebook
  first; if it fails there too, the package needs to be installed (in
  your home conda env, or — for shared use — baked into the JupyterLab
  image by your operator).
- **`Address already in use`** — happens if you start the same script
  twice in the same pod from a terminal. Stop the jhub-apps app from
  the launcher and recreate.
- **Hangs at "Pending"** — the app pod can't get scheduled; same
  causes as a spawner timeout.

## Reference

- Pack [README](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/README.md) — operator-side install, configuration, full `values.yaml` reference
- [jhub-apps docs](https://jhub-apps.nebari.dev/) — framework choices, app configuration, REST API
- [Zero to JupyterHub](https://z2jh.jupyter.org/) — the upstream JupyterHub Helm chart this pack subcharts
- [Nebari docs](https://nebari.dev/docs/) — the broader Nebari distribution

## Next steps

- For longer-lived apps that survive cluster restarts, ask your
  operator to declare them in the chart's
  `jupyterhub.custom.japps-config.startup_apps` instead of creating
  them through the launcher.
- If you need GPUs, ask your operator to add a GPU profile to
  `jupyterhub.custom.profiles` with `runtimeClassName: nvidia` and a
  GPU resource request.
- If your work needs an extra package on every spawn, ask your operator
  to bake it into the JupyterLab image rather than `pip install`-ing
  in your home directory — pod restarts wipe `pip install --user`
  installs unless they live in a persistent shared env.
