---
title: Deployment
description: Operator-facing material for the Nebari Data Science Pack — install paths, architecture, configuration knobs, and troubleshooting.
sidebar_position: 1
---

# Deployment

If you are an operator standing up the Nebari Data Science Pack on a
Kubernetes or Nebari cluster, the pages in this section walk you
through everything you need: installing the chart, configuring the
knobs your team will care about, understanding how the resources fit
together at runtime, and recovering when something breaks.

End users connecting to a cluster that already runs the pack should
head to [User Guides → Use the pack from a notebook →](../how-tos/use_pack_from_notebook)
instead.

## Pick your install path

The pack supports two install paths — pick the one that matches your
environment:

- **If you have a Nebari cluster** with the nebari-operator and Envoy
  Gateway already installed — the recommended production path is
  ArgoCD + GitOps. The chart emits a NebariApp resource that the
  operator picks up to provision routing, TLS, and the Keycloak OIDC
  client. Learn how to [deploy via ArgoCD →](./deploy#nebari-install-argocd--gitops)
- **If you have a plain Kubernetes cluster** (including a local
  [kind](https://kind.sigs.k8s.io/) or [k3d](https://k3d.io/) cluster)
  — the standalone path uses `helm install` directly with the default
  `dummy` authenticator. The simplest way to evaluate the pack or run
  it in CI. Learn how to [deploy standalone →](./deploy#standalone-install-no-nebari)

## What's in this section

- **[Deploy the pack →](./deploy)** — install walkthrough for both
  paths, with prerequisites and post-install verification.
- **[Architecture →](./architecture)** — the Kubernetes resources the
  chart creates and how they interact during install, spawn, and
  login.
- **[Configuration guide →](./configuration_guide)** — the chart
  values you'll most often touch: NebariApp routing, profiles, shared
  storage, Keycloak OAuth, RBAC bootstrap, and Nebi integration.
- **[Troubleshoot →](./troubleshoot)** — symptom-first recovery steps
  for the failures operators and end users hit most often.
