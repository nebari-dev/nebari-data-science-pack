+++
title = "Documentation"
weight = 1
description = "Install, run, and develop the Data Science Pack Helm chart."
+++

The Data Science Pack is a Helm chart for deploying JupyterHub with
[jhub-apps](https://github.com/nebari-dev/jhub-apps) on Kubernetes. It ships
Nebari's custom images, jhub-apps integration for deploying data science
applications, and a dummy authenticator for local development (OAuth and Keycloak
are configurable for production).

{{< cards >}}
{{< card title="Quickstart" href="/guides/quickstart/" >}}
Install the chart from the Helm repository and log in to JupyterHub.
{{< /card >}}
{{< card title="Installation" href="/guides/installation/" >}}
Install from the Helm repository or from source, then access the hub.
{{< /card >}}
{{< card title="Local Development" href="/guides/local-development/" >}}
Spin up a local k3d cluster with a Tilt dev loop in one command.
{{< /card >}}
{{< card title="Shared Storage" href="/guides/shared-storage/" >}}
Mount per-group shared directories into every user pod.
{{< /card >}}
{{< /cards >}}

## What it deploys

The chart wraps the upstream [JupyterHub Helm chart](https://z2jh.jupyter.org/),
so every `jupyterhub.*` value is passed through. On top of that it adds jhub-apps,
shared storage, and the wiring that connects them.

See the [Reference](/reference/) section for the configuration values, the
architecture, and the release process.
