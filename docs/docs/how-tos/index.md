---
title: How-to guides
description: Task-oriented guides for end users of the Nebari Data Science Pack — start a server, pick a profile, deploy apps through jhub-apps, troubleshoot common failures.
sidebar_position: 2
---

# How-to guides

This section is for **end users** on a cluster that already has the pack
installed. If you're trying to install the pack itself, see
[Get started](../get-started/) instead.

The how-tos assume:

- You have an account on the Nebari cluster (Keycloak SSO in production,
  or any username/password in local dev).
- Your operator has confirmed the hub and proxy pods are `Running` and
  given you the JupyterHub URL (`https://jupyter.<your-cluster>` in
  production, or `http://localhost:8000` after a `kubectl port-forward`
  in local dev).

## What's in this section

- **[Use the pack from a notebook](./use)** — start a JupyterLab server,
  pick a profile, work with `/shared/<group>` directories, and deploy
  apps through the jhub-apps launcher.
- **[Troubleshoot](./troubleshoot)** — consolidated index of common
  failure modes (login redirect loops, spawner timeouts, missing shared
  directories, jhub-apps registration errors), with links to the deeper
  per-section troubleshooting blocks in the Use and Deploy guides.
