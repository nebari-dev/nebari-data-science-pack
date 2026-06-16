+++
title = "Installation"
weight = 3
description = "Install the chart from the Helm repository or from source."
+++

You can install the Data Science Pack from the published Helm repository or
directly from source.

{{< tabs >}}
{{< tab title="Helm repository" >}}
```bash
helm repo add nebari https://nebari-dev.github.io/nebari-data-science-pack
helm repo update
helm install data-science-pack nebari/nebari-data-science-pack
```
{{< /tab >}}
{{< tab title="From source" >}}
```bash
git clone https://github.com/nebari-dev/nebari-data-science-pack.git
cd nebari-data-science-pack
helm dependency update
helm install data-science-pack . --namespace default
```
{{< /tab >}}
{{< /tabs >}}

## Access JupyterHub

Once the release is installed, forward the proxy service:

```bash
kubectl port-forward svc/proxy-public 8000:80
```

Open [http://localhost:8000](http://localhost:8000). With the dummy
authenticator, any username and password works.

## Configuration

See [`values.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/values.yaml)
for all options, or the [Configuration reference](/reference/configuration/). The
chart wraps the [JupyterHub Helm chart](https://z2jh.jupyter.org/), so every
`jupyterhub.*` value is passed through.
