# Documentation site

The docs site for the Data Science Pack, built with [Hugo](https://gohugo.io/)
and the Darby theme.

## Build locally

```bash
cd site
hugo server          # live preview at the printed localhost URL
```

The theme is consumed as a Hugo module (`github.com/aktech/darby`). `go.mod`
uses a local `replace` for development; point it at your checkout of the theme.

## Ask Assistant index

The in-browser Q&A needs a prebuilt retrieval index. Build it from the rendered
site (run from the theme checkout, which carries the indexer and its deps):

```bash
hugo --cleanDestinationDir              # render to site/public
node <theme>/scripts/build-index.mjs \
  --source public \
  --base https://nebari-dev.github.io/nebari-data-science-pack/docs/ \
  --out public/assistant-index.json
```

## Deploy

The site is published to the `gh-pages` branch under `docs/`, so it serves at
`https://nebari-dev.github.io/nebari-data-science-pack/docs/`. The Helm chart
repository stays at the `gh-pages` root and is untouched.
