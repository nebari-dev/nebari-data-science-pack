---
title: Release notes
description: Tagged releases of the Nebari Data Science Pack — what shipped in each version and links to the GitHub releases page.
sidebar_position: 2
---

# Release notes

The pack's current chart version is in
[`Chart.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/Chart.yaml).
At time of writing, releases follow the pattern `0.1.0-alpha.<n>`.

Every push to `main` that bumps `Chart.yaml` triggers
[`.github/workflows/release.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/.github/workflows/release.yaml),
which creates a GitHub release with auto-generated notes (from PR
titles since the last tag) and uploads the packaged `.tgz` chart as
a release asset.

## Where to find each release

- **Tagged releases** —
  [github.com/nebari-dev/nebari-data-science-pack/releases](https://github.com/nebari-dev/nebari-data-science-pack/releases).
  Each tag has a GitHub release with auto-generated notes and a
  packaged `.tgz` chart asset.
- **Latest chart version** — pinned in
  [`Chart.yaml`](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/Chart.yaml)
  on `main`.
- **Helm repository** — released charts are published via the
  `gh-pages` branch with `helm repo index`; the consumer URL is
  `https://nebari-dev.github.io/nebari-data-science-pack` (see
  [Deploy the pack](../get-started/deploy#from-the-helm-repository)).

## Versioning

| Field | Source | Meaning |
|---|---|---|
| `version` in `Chart.yaml` | Helm | Chart version — bumped on every release |
| `appVersion` in `Chart.yaml` | Helm | Pack application version |
| `dependencies[].version` | Helm | Pinned z2jh subchart version |
| Image `tag` in `values.yaml` | Pack | Hub / JupyterLab / Nebi container builds — bumped by `scripts/bump_image_tags.py` |

The version string follows the
[SemVer pre-release format](https://semver.org/#spec-item-9)
(`MAJOR.MINOR.PATCH-PRERELEASE`); the leading `0.1.0` and the
`alpha.<n>` qualifier signal that the chart API surface is still
evolving. Always read the auto-generated notes for each tag before
upgrading — and pin to a specific tag in your ArgoCD `targetRevision`
rather than tracking `main`.

## Upgrading

For ArgoCD-managed deployments, bump `targetRevision` in the
`Application` manifest and let GitOps reconcile. For manual `helm
upgrade`, see [Deploy the pack](../get-started/deploy).

The Keycloak RBAC bootstrap Job is idempotent (see
[Configuration guide → Keycloak RBAC bootstrap](../get-started/configuration_guide#keycloak-rbac-bootstrap)),
so re-runs across upgrades are safe.

## Reporting issues with a release

If a tagged release behaves differently from its notes, open an issue
at
[nebari-data-science-pack/issues](https://github.com/nebari-dev/nebari-data-science-pack/issues)
and include:

- The exact chart version (from `Chart.yaml` or the Helm release).
- Whether the install was standalone or via ArgoCD.
- The output of the [first checks](../get-started/troubleshoot#first-checks).
