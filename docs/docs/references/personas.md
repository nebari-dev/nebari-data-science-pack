---
title: Personas
description: Who this documentation is written for — operators, end users, contributors — and where each persona should start.
sidebar_position: 3
---

# Personas

This page describes the reader types this documentation is written
for and shows each one where to start. The docs are cross-linked, so
you can follow threads across personas as your needs change — but
starting in the right place saves time.

## If you are an end user

You have an account on a Nebari cluster somebody else operates. You
want to open a JupyterLab notebook, work with shared team data, and
deploy a Streamlit / Panel / Voilà app from the launcher. You don't
need (and don't want) to run `kubectl`.

**Start here:**

- Learn how to [use the pack from a notebook →](../how-tos/use_pack_from_notebook)

When you hit something you can't fix yourself, hand the error string
to your operator and link them at
[Deployment → Troubleshoot →](../get-started/troubleshoot).

## If you are an operator

You run the cluster. You install Helm charts, configure ingress and
TLS, wire OIDC against Keycloak, manage shared storage, and you're
on-call for spawner / hub / proxy failures.

**Start here:**

- Learn how to [deploy the pack →](../get-started/deploy) (install paths)
- Learn how to [configure the chart →](../get-started/configuration_guide) (the knobs you'll touch)
- Read the [architecture overview →](../get-started/architecture) (how resources interact at runtime)

When something breaks, the
[Troubleshoot →](../get-started/troubleshoot) page is the
symptom-first recovery index.

## If you are a platform contributor

You're contributing to the pack itself — adding chart values, fixing
hub config files, adjusting the operator integration. You need to
understand both the chart internals and how it appears to operators.

**Start here:**

- Read the [architecture overview →](../get-started/architecture) for the resource model
- Browse the [`values.yaml` reference →](./values) for the full configuration surface
- Check the repo's
  [`README.md`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/README.md)
  and `AGENT.md` for the development workflow and docs conventions

For PRs that change behavior or defaults, update the corresponding
[Configuration guide →](../get-started/configuration_guide) section
and add an entry to the next [Release notes →](./release_notes) tag.

## If you are evaluating the pack

You're considering the pack for your cluster but haven't installed it
yet. You want to know what it does, what it requires, and how it
compares to bare z2jh.

**Start here:**

- Read the [Introduction →](../) for the overview
- Check the [prerequisites →](../get-started/deploy#prerequisites) for what you'd need to bring
- Skim the [architecture overview →](../get-started/architecture) for the runtime picture

If you want to see it working end-to-end before committing, the
**Standalone install** path in
[Deploy the pack →](../get-started/deploy#standalone-install-no-nebari)
runs against a local kind / k3d cluster with no Nebari dependencies.
