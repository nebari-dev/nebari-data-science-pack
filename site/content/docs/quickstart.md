+++
title = "Quickstart"
weight = 2
description = "Install the chart from the Helm repository and log in to JupyterHub."
+++

This quickstart installs the Data Science Pack from the Helm repository and gets
you logged in to JupyterHub.

{{< steps >}}
1. Add the Helm repository and update.
2. Install the chart.
3. Port-forward the proxy and open the hub.
4. Log in with the dummy authenticator.
{{< /steps >}}

## Install from the Helm repository

```bash
helm repo add nebari https://nebari-dev.github.io/nebari-data-science-pack
helm repo update
helm install data-science-pack nebari/nebari-data-science-pack
```

## Access JupyterHub

Port-forward the proxy service to your machine:

```bash
kubectl port-forward svc/proxy-public 8000:80
```

Then open [http://localhost:8000](http://localhost:8000).

{{< callout type="note" title="Dummy auth" >}}
With the default dummy authenticator, any username and password works. Switch to
OAuth via Keycloak for production. See [Configuration](/reference/configuration/).
{{< /callout >}}

## Next steps

- [Installation](/docs/installation/) covers installing from source.
- [Local Development](/docs/local-development/) sets up a live dev loop.
- [Configuration](/reference/configuration/) lists every value you can set.
