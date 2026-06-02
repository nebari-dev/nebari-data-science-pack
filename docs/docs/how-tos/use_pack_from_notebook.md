---
title: Use the pack from a notebook
description: Log in to JupyterHub, pick a profile, work with shared storage, and deploy apps through the jhub-apps launcher.
sidebar_position: 1
---

# Use the pack from a notebook

End-user guide for the Nebari Data Science Pack. Walks through logging
in to JupyterLab, picking a profile, working with `/shared/<group>`,
and deploying apps through jhub-apps. If something doesn't work,
[ask your operator](../get-started/troubleshoot) — most failures
need cluster access to investigate.

## Step 1 — Log in

Open the hub URL your operator gave you. In production it looks like
`https://jupyter.<your-cluster>`; on a local dev cluster it's typically
`http://localhost:8000`. If you don't have a URL yet, ask your operator.

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
[Troubleshoot → Spawner timeout](../get-started/troubleshoot#spawner-times-out-during-startup).

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
[Troubleshoot → /shared empty](../get-started/troubleshoot#shared-directories-empty).

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

The app keeps running after you close your browser — jhub-apps does
not stop apps when you sign out. **Stop the app from the launcher when
you're done**, otherwise it holds a pod indefinitely.

### Idle culling — what gets stopped automatically

Two cullers run in the background. Knowing what each one does helps
you avoid losing in-progress work:

| What | When it runs | What it kills |
|---|---|---|
| **Hub-level culler** ([`jupyterhub-idle-culler`](https://github.com/jupyterhub/jupyterhub-idle-culler)) | After 30 min with no notebook activity | Your entire JupyterLab server (pod is stopped; on next login a fresh one is spawned) |
| **Per-pod culler** (`singleuserCuller`) | After 15 min with no kernel / terminal activity | Idle kernels and terminals inside your running JupyterLab pod (the pod stays up; restart the kernel when you come back) |
| Neither | — | jhub-apps deployments. They stay up until you stop them. |

Two practical implications:

- **Long-running computations** — start them from a notebook cell so
  the kernel is "busy" (the culler treats busy kernels as active). A
  long shell command in a terminal does not count as activity.
- **Leaving the tab open isn't enough** — the per-pod culler doesn't
  check browser activity, only kernel / terminal activity. Save your
  work before stepping away.

If a kernel was culled, just re-run the cell — the kernel restarts
automatically. If the whole server was culled, log back in and your
home directory and `/shared` mounts come back exactly as you left them.

## Step 5 — Shared environments via Nebi (when enabled)

[Nebi](https://github.com/nebari-dev/nebari-nebi-pack) is a Nebari
companion service that lets teams publish shared Python / conda
environments — so everyone in the team picks the same versions from
the JupyterLab launcher instead of installing them individually.

If your cluster has Nebi set up, you'll see published team
environments in the JupyterLab launcher alongside the per-user
environments. No extra login is needed.

If you expected shared team environments but only see local ones,
ask your operator — Nebi may not be deployed on this cluster.

## Accessing the hub from outside the cluster

In production the hub is reachable at `https://jupyter.<your-cluster>`
via Envoy Gateway, TLS-terminated, and OIDC-gated by Keycloak. The
first request returns a 302 to Keycloak; after login, a session cookie
is set and subsequent requests pass through.

If your operator runs the pack without the NebariApp routing layer
(common for local dev), the hub isn't exposed publicly — your operator
will give you a local URL (typically `http://localhost:8000`) instead.

## Troubleshooting

### Login redirects in a loop

The hub OAuth client's `rootUrl` / `baseUrl` aren't set in Keycloak, so
the hub never sees the `oauthenticator-state` cookie that pairs the
login request with the callback.

Symptom: after Keycloak login you bounce back to the login page, or
get `400 OAuth state mismatch`.

Ask your operator to re-run the
[Keycloak RBAC bootstrap Job](../get-started/configuration_guide#keycloak-rbac-bootstrap)
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
[Troubleshoot → `/shared/<group>` directories empty](../get-started/troubleshoot#shared-directories-empty).

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

- [Architecture](../get-started/architecture) — how the pack's
  components fit together (helpful when an error message names one).
- [Deploy the pack](../get-started/deploy) — what your operator
  installed; useful background when you need to ask for a config
  change.
- [`values.yaml` reference](../references/values) — every chart value
  your operator can tune.
- [jhub-apps docs](https://jhub-apps.nebari.dev/) — upstream
  documentation for the launcher: framework choices, REST API.

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
