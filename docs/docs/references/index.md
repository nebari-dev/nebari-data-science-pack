---
title: Reference
description: Full reference for the Nebari Data Science Pack — values.yaml options, architecture, and Kubernetes resources.
sidebar_position: 3
---

# Reference

Look-up material for the pack: every chart value, the Kubernetes
resources the pack creates at runtime, and the relationships between
them.

## What's in this section

- **[`values.yaml` reference](./values)** — every chart value with its
  default, type, and a one-line description. Grouped by area (NebariApp,
  singleuser culler, shared storage, Nebi, RBAC bootstrap, JupyterHub
  subchart overrides).
- **[Architecture](./architecture)** — the Kubernetes resources the
  pack creates (hub, proxy, jhub-apps, NebariApp, Keycloak bootstrap
  Job, shared PVC, NFS server) and how they interact during install,
  spawn, and login.
