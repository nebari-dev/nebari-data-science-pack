+++
title = "Data Science Pack"
description = "A Helm chart for deploying JupyterHub with jhub-apps on Kubernetes."
badge = "Nebari pack"
heroTitle = "JupyterHub and data science apps, packaged for Kubernetes"
heroSubtitle = "The Data Science Pack is a Helm chart that deploys JupyterHub with jhub-apps, Nebari's custom images, and shared storage. One chart, sensible defaults, ready to run."
ctaText = "Get started"
ctaURL = "/docs/quickstart/"
heroCodeName = "install.sh"
heroCode = """
$ helm repo add nebari \\
    https://nebari-dev.github.io/nebari-data-science-pack
$ helm repo update
$ helm install data-science-pack nebari/nebari-data-science-pack
$ kubectl port-forward svc/proxy-public 8000:80

JupyterHub is now running at http://localhost:8000
"""
featuresTitle = "What the chart gives you"
featuresSubtitle = "Install the chart, port-forward, and log in. The defaults are tuned for a working deploy from a single required field."

ctaBandTitle = "Ready to deploy?"
ctaBandSubtitle = "Add the Helm repo and install in two commands."

[[features]]
  icon = "config"
  title = "JupyterHub, packaged"
  body = "Wraps the upstream JupyterHub Helm chart with Nebari's custom hub and singleuser images."
  wide = true
[[features]]
  icon = "nav"
  title = "jhub-apps integration"
  body = "Deploy and share data science applications (Panel, Streamlit, Voila, and more) straight from the hub."
[[features]]
  icon = "callout"
  title = "Shared storage"
  body = "Per-group shared directories mounted into every user pod, backed by an RWX storage class."
[[features]]
  icon = "theme"
  title = "Pluggable auth"
  body = "A dummy authenticator for local development; OAuth via Keycloak for production deploys."
[[features]]
  icon = "code"
  title = "Zero-config defaults"
  body = "A fresh deploy needs only one field. Everything else is derived by subdomain convention and override-able."
[[features]]
  icon = "search"
  title = "Local dev loop"
  body = "A k3d plus Tilt setup gives you a live development loop with one make command."
+++

The Data Science Pack is a Nebari software pack. It bundles JupyterHub, jhub-apps,
and shared storage into a single Helm chart you can install on any Kubernetes cluster.
