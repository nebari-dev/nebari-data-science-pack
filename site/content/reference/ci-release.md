+++
title = "CI/CD and Releasing"
weight = 3
description = "The workflows that lint, test, and publish the chart."
+++

## Workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `lint.yaml` | push / PR | Helm lint and template validation. |
| `test.yaml` | push / PR | Full deployment test on k3d. |
| `release.yaml` | push to `main` | Publish chart to GitHub Pages. |

## Releasing

To release a new version:

{{< steps >}}
1. Update `version` in `Chart.yaml`.
2. Push to `main`.
3. The release workflow creates a GitHub release tagged with the chart version and publishes the chart to GitHub Pages.
{{< /steps >}}

{{< callout type="note" title="First release" >}}
Enable GitHub Pages on the `gh-pages` branch in the repository settings after the
first release.
{{< /callout >}}

## License

Apache License 2.0. See
[LICENSE](https://github.com/nebari-dev/nebari-data-science-pack/blob/main/LICENSE)
for details.
