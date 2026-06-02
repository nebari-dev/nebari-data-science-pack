---
title: User Guides
description: End-user material for the Nebari Data Science Pack — log in to JupyterLab, pick a profile, work with /shared, deploy apps through jhub-apps.
sidebar_position: 2
---

# User Guides

If you are a notebook user on a cluster that already runs the Nebari
Data Science Pack, the pages in this section walk you through what
you'll do day-to-day: signing in, picking a profile, sharing work
with your team, and deploying apps from the launcher.

If you're trying to install the pack itself, you're an operator —
head to [Deployment → Deploy the pack →](../get-started/deploy)
instead.

## Before you start

You'll need:

- An account on the Nebari cluster (Keycloak SSO in production, or
  any username/password in local dev).
- The JupyterHub URL your operator gave you — typically
  `https://jupyter.<your-cluster>` in production, or a local URL
  like `http://localhost:8000` in dev.

If you're missing either, reach out to whoever runs your cluster.

## What's in this section

- **[Use the pack from a notebook →](./use_pack_from_notebook)** —
  learn how to log in, pick a profile, work with `/shared/<group>`
  directories, deploy apps through the jhub-apps launcher, and
  recover from common notebook-side issues.

When something breaks that you can't fix from the notebook side, hand
the error to your operator and link them at
[Deployment → Troubleshoot →](../get-started/troubleshoot).
