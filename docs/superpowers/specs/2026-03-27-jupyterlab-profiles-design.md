# JupyterLab Profiles — Design Spec

**Date:** 2026-03-27
**Status:** Approved

## Goal

Expose a profile selector in JupyterHub so users can choose their resource allocation (CPU / RAM) before spawning a JupyterLab pod. Matches the profile experience from classic Nebari.

## Scope

- CPU and memory sizing only (no GPU, no custom images in this iteration)
- Access model: `all` — every authenticated user sees every profile
- Two default profiles: Small and Medium
- Deployers can override the full list via their deployment values file

## Out of Scope

- Per-user or per-group access control (`yaml` / `keycloak` access modes)
- GPU profiles (`node_selector`, `extra_resource_limits`)
- Custom image per profile
- Profile options (sub-choices within a profile)

## Design

### values.yaml

Add `profiles` list under `jupyterhub.custom.profiles`. Default ships two profiles:

```yaml
jupyterhub:
  custom:
    profiles:
      - display_name: "Small"
        description: "1 CPU / 2 GB RAM"
        default: true
        kubespawner_override:
          cpu_limit: 1
          cpu_guarantee: 0.5
          mem_limit: "2G"
          mem_guarantee: "1G"
      - display_name: "Medium"
        description: "4 CPU / 8 GB RAM"
        kubespawner_override:
          cpu_limit: 4
          cpu_guarantee: 2
          mem_limit: "8G"
          mem_guarantee: "4G"
```

Deployers override the entire list in their deployment-specific values file. Any valid KubeSpawner trait is accepted in `kubespawner_override` — this means GPU (`extra_resource_limits`), `node_selector`, and `image` all work in the future without code changes.

### config/jupyterhub/01-spawner.py

Add one section after the existing environment variable setup:

```python
# ---------------------------------------------------------------------------
# Profiles (resource sizing)
# ---------------------------------------------------------------------------
profiles = get_config("custom.profiles", [])
if profiles:
    c.KubeSpawner.profile_list = profiles
    log.info("profiles: loaded %d profile(s)", len(profiles))
else:
    log.info("profiles: none configured, single-instance mode")
```

No other changes. KubeSpawner applies `kubespawner_override` natively.

### Interaction with pre_spawn_hook

KubeSpawner applies `kubespawner_override` (cpu/mem) first, then calls `pre_spawn_hook`. The existing hook (NSS wrapper, shared storage mounts, Nebi auth) runs on top of whichever profile the user picked. No conflict.

### Behaviour when profiles list is empty

If `custom.profiles` is absent or `[]`, `c.KubeSpawner.profile_list` is not set and JupyterHub spawns a single pod with no selector shown. Existing behaviour is fully preserved.

## Files Changed

| File | Change |
|------|--------|
| `values.yaml` | Add `jupyterhub.custom.profiles` with Small and Medium defaults |
| `config/jupyterhub/01-spawner.py` | Read profiles, set `c.KubeSpawner.profile_list` if non-empty |

## Future Extensions (not in scope now)

- Add `access: yaml` and `access: keycloak` support by replacing the static list with an async `render_profiles(spawner)` callable — no values.yaml changes needed
- GPU profiles: add `node_selector` and `extra_resource_limits` to a profile's `kubespawner_override` — already supported by KubeSpawner, zero code changes
- Custom image per profile: add `image` to `kubespawner_override` — same story
