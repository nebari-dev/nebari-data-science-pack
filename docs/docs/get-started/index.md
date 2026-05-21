---
title: Get started
description: Install the Nebari Data Science Pack on a standalone Kubernetes cluster or via ArgoCD on Nebari.
sidebar_position: 1
---

# Get started

This section is for **operators** installing the pack on a Kubernetes cluster.

The pack supports two install paths:

- **Standalone** — `helm install` against any Kubernetes cluster, including
  a local [kind](https://kind.sigs.k8s.io/) or
  [k3d](https://k3d.io/) cluster. The simplest path for local dev and CI;
  no Nebari dependencies. Access JupyterHub via `kubectl port-forward` and
  the default `dummy` authenticator (any username/password works).
- **Nebari (ArgoCD + GitOps)** — the recommended production path. The chart
  creates a NebariApp resource that the nebari-operator picks up to
  provision Envoy Gateway routing, TLS, and the Keycloak OIDC client.
  Requires the nebari-operator and Envoy Gateway to already be installed.

End users connecting to an already-deployed cluster should jump to
[How-to guides](../how-tos/) instead.

## What's in this section

- **[Deploy the pack](./deploy)** — the full install walkthrough for both
  paths, plus configuration knobs (NebariApp, profiles, shared storage,
  Keycloak OAuth, Nebi integration) and the operator troubleshooting
  index.
