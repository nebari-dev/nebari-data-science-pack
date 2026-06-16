+++
title = "Local Development"
weight = 4
description = "Spin up a local k3d cluster with a Tilt dev loop in one command."
+++

The chart ships a local development setup built on a k3d cluster and a Tilt loop,
so you can iterate on the chart against a real cluster on your machine.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [ctlptl](https://github.com/tilt-dev/ctlptl)
- [Tilt](https://docs.tilt.dev/install.html)

## Start the dev loop

```bash
# Start local k3d cluster + Tilt dev loop
make up
```

This brings up a local k3d cluster and starts Tilt.

| Surface | URL |
|---------|-----|
| Tilt UI | [http://localhost:10350](http://localhost:10350) |
| JupyterHub | [http://localhost:8000](http://localhost:8000) |

## Tear down

```bash
make down
```

{{< callout type="tip" title="Editing values" >}}
Changes to `values.yaml` and the templates are picked up by the Tilt loop, so
you can edit the chart and watch the deploy reconcile live in the Tilt UI.
{{< /callout >}}
