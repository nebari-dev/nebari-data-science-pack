# AGENT.md — Docs-site playbook

A field guide for anyone (human or AI agent) standing up a documentation
site for a similar OSS project — particularly a Helm chart, Kubernetes
operator, or platform plugin where readers split cleanly into
"operators who install it" and "end users who consume it."

It captures what worked and what got us churned through review on the
`nebari-rayserve-pack` docs build. Read it before writing the first page;
re-read it before opening the PR.

---

## 1. Stack and project layout

### Toolchain (this repo)
- **Docusaurus 3.5.2** — static-site generator with sidebar, search, MDX, Mermaid, dark mode out of the box.
- **Yarn (classic v1)** — `package.json` uses `yarn`, not `npm`. Don't mix lockfiles.
- **Netlify** — preview deploy per PR, auto-deploy on merge to `main`. Config in `netlify.toml`.
- **GitHub Pages alternative**: works too via `yarn deploy`; we picked Netlify for built-in PR previews.

### Repo layout
```
<repo-root>/
├── chart/                         # the Helm chart this docs site documents
│   ├── Chart.yaml                 # source of truth for chart/app version
│   ├── values.yaml                # source of truth for every documented value
│   └── templates/                 # source of truth for resources, ports, services
├── docs/                          # Docusaurus site
│   ├── docs/                      # markdown content (folder per audience)
│   │   ├── introduction.mdx       # site root (`slug: /`)
│   │   ├── get-started/           # operator-facing install + ops
│   │   ├── how-tos/               # end-user task guides
│   │   └── references/            # lookup material (values reference, architecture)
│   ├── static/img/screenshots/    # PNGs from real deployments
│   ├── sidebars.js                # navigation tree
│   ├── docusaurus.config.js       # site config, theme, plugins
│   └── package.json
├── netlify.toml                   # build cmd + publish dir
├── README.md                      # project entry on GitHub (not the docs site)
└── AGENT.md                       # this file
```

### Local commands
```bash
cd docs
yarn install          # first time / after lockfile changes
yarn start            # dev server with hot reload (localhost:3000)
yarn build            # static build to docs/build/ — runs broken-link check
yarn serve            # serve the build output locally
yarn clear            # nuke Docusaurus build cache if hot reload breaks
```

`yarn build` is the single best pre-flight check. It catches broken
relative links, missing pages, and Mermaid syntax errors that `yarn start`
will silently let through.

---

## 2. Information architecture

### The split that matters most: end user vs operator

This is the rule that drives almost every other rule. Decide it before
writing a single sentence.

- **End-user docs (`how-tos/`)** — reader has a notebook on a cluster
  somebody else set up. **Never** include `kubectl`, `helm`, or
  cluster-admin commands. When the answer requires cluster access, say
  "ask your operator" and link to the operator-side fix.
- **Operator docs (`get-started/`)** — reader installs and runs the
  platform. `kubectl`, `helm`, `argocd`, `gateway api`, etc. are fine
  here. Every operator-troubleshooting heading should be a target for
  end-user "ask your operator" links.
- **Reference (`references/`)** — lookup material, audience-agnostic.
  Tables of values, architecture diagrams, port lists. No prose
  walkthroughs.

**Sub-rule:** when one topic spans both audiences, split the file. We
initially had one `use.md` mixing both. The reviewer forced a full
rewrite + rename to `use_ray_from_notebook.md`. Cheap to do right; very
expensive to fix after the fact.

**Filename convention:** describe the task ("use_ray_from_notebook"),
not the verb ("use"). Filenames become URLs become anchors become titles
on link previews — pick names that read well in all of those contexts.

### Diátaxis-ish mapping
| Diátaxis quadrant | This site's folder |
|---|---|
| Tutorial (learning-oriented) | skipped — small audience, mostly task-driven |
| How-to (task-oriented) | `how-tos/` |
| Reference (information-oriented) | `references/` |
| Explanation (understanding-oriented) | `references/architecture.md` |

### Sidebar
Hand-curated in `sidebars.js` — not auto-generated. Each section has an
index page; the section's link in the sidebar points at the index
(`link: { type: 'doc', id: 'how-tos/index' }`), and the index page does
the "what's in this section" routing.

---

## 3. Writing conventions

### Voice
- Direct, concise, active voice. No marketing tone.
- "You" for the reader; "the chart" / "the operator" / "the cluster" for third parties.
- US English. "Behavior" not "behaviour" (the reviewer here flagged it).
- First sentence of each section is the actionable claim. The rest is justification.

### Specific terminology
- Prefer the project's own terms over generic ones when the context is specific:
  - "Nebari cluster" > "Kubernetes cluster" when the context is Nebari
  - "Helm chart" > "Helm release" (chart is the artifact; release is the instance — they're different things and reviewers will catch the mix-up)
- Don't treat composed things as alternatives:
  - **wrong:** "Kubernetes or Nebari" (Nebari runs on Kubernetes)
  - **right:** "Kubernetes (with or without Nebari)"
- Don't invoke components that don't exist in the stack. Verify before naming.

### Things to avoid
- "Screenshot pending" / "TODO" admonitions in published markdown. Either capture or remove — never ship author notes.
- Burying the lede behind preamble. Lead with the action.
- Long YAML blocks where a 2-line summary + link to `values.yaml` would do.
- Marketing voice ("seamlessly", "powerful", "robust"). Cut.

### The stale-version trap (most common smell)
Any literal version number baked into prose or tables is a timebomb.
The reviewer killed our intro page's "At a glance" table for exactly
this reason — and the same liability quietly migrated into our deploy
guide before round 2 caught it.

Mitigation hierarchy (best to worst):

1. Don't pin in prose at all — use `<your-ray-version>` placeholders in examples.
2. Link to the source-of-truth file (`chart/values.yaml`) and tell the reader to check there.
3. Stamp the page with `:::note[Defaults reflect chart vX.Y.Z]` so at least the reader knows when the doc was true.
4. Hardcode without context — worst, never do this.

Apply the same logic to API versions, image tags, port numbers (unless they're protocol-fixed like 443/80), and dependency minimums.

### Cross-references
- **Relative links** (`../get-started/deploy`) so they survive hostname / base-path changes.
- **Anchor links** are auto-generated by Docusaurus as kebab-case-lowercased headings. Verify by visiting the page; typos render as broken silently.
- **No circular references.** Every "see X" link should land somewhere with actionable content. If `A links to B for the fix` and `B links to A for the fix`, the reader is in a loop. Audit before merging.
- **No off-site bounces when on-site exists.** If your docs cover it, link there before linking to GitHub README or upstream guides. Reserve external links for canonical upstream (Ray docs, K8s docs, RFC, etc.).

### Code blocks
- Always set the language hint (` ```yaml `, ` ```bash `, ` ```python `) — drives syntax highlighting.
- Use realistic but generic values: `example.com`, `your-cluster`, `<your-version>`. Never customer or internal names.
- For multi-step shell sequences, comment each step.
- For Python that you claim does X — actually run it. We shipped `print(ray.__version__)` after `ray.init()` claiming it would print the *cluster's* version. It prints the *local client's* version. Reviewer didn't catch it; the next user would have.

### Admonitions
Docusaurus syntax: `:::warning[Custom title]` ... `:::`. Use the custom title slot — "Warning" alone is wasted space.

| Admonition | Use for |
|---|---|
| `:::note` | Incidental context that doesn't fit prose flow. |
| `:::tip` | Optional shortcut or optimization. |
| `:::info` | Orientation; helpful but not load-bearing. |
| `:::warning` | Likely to bite the reader if ignored (version match, callback URI, network policy). |
| `:::danger` | Irreversible / data-loss / security implications. |

Don't overuse — they lose impact. One per H2-section is usually plenty.

### Tables
- Every table needs a header row. `| | |` renders empty headers — broken.
- 3-4 columns max for readability on mobile.
- For reference tables that grow past ~20 rows: split by topic under H3 headers.
- Right-align numeric columns with `|---:|`.

### Diagrams (Mermaid)
- Enabled in `docusaurus.config.js` via `markdown: { mermaid: true }` and `themes: ['@docusaurus/theme-mermaid']`.
- Use flowcharts for component models, sequence diagrams for request flow, state diagrams for lifecycles.
- **Verify against code.** Easy to draw a diagram that contradicts the templates. We shipped one where the dashboard NebariApp route was missing entirely — readable bug, only caught on a re-review pass.
- Color subgraphs to encode meaning. Pick a small palette and stick to it across all diagrams.
- Label optional / opt-in components in the diagram — don't hide them.

### Screenshots
- `docs/static/img/screenshots/` — kebab-case descriptive filenames (`dashboard-serve-healthy.png`, not `Screenshot1.png`).
- Capture against real deployments. Don't mock UIs in Figma — they drift from reality and readers spot it.
- Alt text matters: `![Ray Dashboard Serve tab with the hello app running and one healthy replica]` is what screen readers and search indexers see.
- Multiple states for troubleshooting docs: capture healthy AND failure side-by-side; failure shots are higher signal.
- Strip browser chrome, address bars with internal hostnames, real user names and avatars.
- If you don't have it yet, leave the section out entirely — never ship `:::info[Screenshot pending]`.

### Frontmatter
Every page needs:
```yaml
---
title: <H1 and tab title>
description: <one-sentence summary; powers search and social previews>
sidebar_position: <int; controls order in sidebar>
---
```
`slug: /` on the intro page makes it the site root. `slug:` elsewhere overrides the auto-generated URL.

---

## 4. Verification habits

The doc claim is only as good as the source you checked. Most "wait, that's not right" review rounds trace back to writing from memory.

| Claim type | Source of truth |
|---|---|
| Chart value name / default | `chart/values.yaml` |
| Container ports / probes / resources | `chart/templates/*.yaml` |
| Service name pattern | `chart/templates/_helpers.tpl` and `services.yaml` |
| Chart / app version | `chart/Chart.yaml` |
| What a controller mutates at runtime | Controller's source / upstream docs — not what the chart applies |
| Python / Ray / Helm version constraints | Project's CI matrix or requirements file, not "the version I tested with" |

### Pre-PR grep sweep
Before opening the PR:

```bash
# Find every place the current literal version appears
grep -rn "2.43.0" docs/

# Find off-site bounces that should be on-site links
grep -rn "github.com.*nebari-rayserve-pack" docs/

# Find leaked author notes
grep -rn "Screenshot pending\|TODO\|FIXME\|XXX\|pending" docs/

# Find broken anchor references (won't catch all, but surfaces obvious typos)
grep -rn "](#" docs/ | grep -i "TODO\|FIXME"
```

### Click-through
- `yarn build` succeeds with zero broken-link warnings.
- `yarn start` and click every link in the sidebar — anchor typos render as "section not found" silently.
- Mermaid diagrams render (syntax errors fail silently in some renderers).

---

## 5. Doc anti-patterns (we hit all of these on round 1)

1. **Mixed-audience pages** → split files at the audience boundary.
2. **Stale-version literals in tables** → link to `values.yaml` and stamp the page with chart version.
3. **`:::info[Screenshot pending]` leaked to readers** → don't draft TODOs into published markdown; track in issues.
4. **Circular "see X" references** → every link should land somewhere actionable, not bounce.
5. **Off-site bounces when on-site exists** → prefer relative links to internal pages.
6. **Duplicate content between deploy guide and reference** → pick canonical; the other links to it. Drift is inevitable when content lives in two places.
7. **Dangling modifiers after applying a copy-edit suggestion** → re-read the sentence after the paste; don't paste blind.
8. **Code blocks that compile but don't do what the prose claims** → run the snippet against a real cluster.
9. **Empty table headers (`| | |`)** → every table needs real header text.
10. **Diagrams that contradict the code** → redraw from the templates, not from memory.

---

## 6. Pre-publish checklist

- [ ] `yarn build` succeeds with zero broken-link warnings
- [ ] `yarn start` and click through every page in the sidebar
- [ ] Every code block runs (Python snippets, kubectl commands, YAML applies cleanly)
- [ ] Every screenshot loads (no 404s)
- [ ] Every anchor link resolves to a real heading
- [ ] grep for the current version literal — every hit is intentional and stamped with a "defaults reflect vX.Y.Z" note
- [ ] grep for `TODO`, `FIXME`, `pending`, `XXX` — zero hits in published markdown
- [ ] Mermaid diagrams render in the browser
- [ ] All `:::admonition` blocks close (a missed `:::` corrupts the rest of the page)
- [ ] Sidebar order matches reading order; sidebar IDs match file paths

---

## 7. Demo + screenshot workflow

When a doc PR needs new screenshots:

1. **Stand up a real instance.** Sandbox or staging cluster, never customer data on screen.
2. **Identify every state you need** before starting capture — healthy, failure, mid-deploy, login, etc. Make a shot list.
3. **Take at 2× / Retina resolution** if possible; Docusaurus downscales cleanly.
4. **Strip identifying info.** Address bars with internal hostnames, real user names/emails, customer org names.
5. **Name files for what they show**, not the order you took them. `dashboard-serve-deploy-failed.png` survives reorganization; `Screenshot12.png` doesn't.
6. **For state-machine docs (`HEALTHY` vs `DEPLOY_FAILED`)**, capture both states in one session against the same dashboard so the visual style matches.

**A specific lesson from our demo:** Ray Serve has a tricky failure-mode distinction. Errors in `__init__` produce `DEPLOY_FAILED` (worker never became ready). Errors in `__call__` leave the deployment `HEALTHY` and return 500s on every request (worker is fine, request path is broken). These look identical at first but need different fixes. If the source project has subtle state-machine distinctions like this, document them with both screenshots side by side.

---

## 8. Reviewer collaboration

Each reviewer has a lens. Capture it explicitly before the next round, not after.

### What to ask the reviewer before writing
- Who is the primary audience for this page?
- Are there terms the project prefers (e.g. "Nebari" over "Kubernetes" in certain contexts)?
- Is there a page they already blessed whose voice I should match?
- What's the freeze policy on the version numbers I'll cite?

### What to do mid-review
- Apply feedback in **one commit per round**, not per comment. Reviewers can read a single delta; they can't track 12 small ones.
- For renames, use `git mv` so blame survives. Heavy concurrent edits will still classify as delete+create in `git status` — that's OK, blame is preserved at the blob level.
- When applying a worded suggestion verbatim, re-read the resulting sentence. Reviewers sometimes leave dangling modifiers without realizing it; pasting blind ships the dangling modifier.

### What to capture for next time
Save reviewer-specific patterns to durable memory (not the PR comment thread, which is hard to search later). Topics worth capturing:
- Audience boundaries the reviewer enforces
- Language preferences (regional spelling, preferred terms, words to avoid)
- Structural preferences (no version tables, no kubectl in end-user docs, etc.)
- Anything they flagged twice — that's a hard rule, not a one-off

---

## 9. Git and commit conventions

- Branch off `main`, push to a feature branch, open PR.
- Commit message style: `docs: <imperative summary>`. Multiline body for the *why* when it's not obvious from the diff.
- This repo: **no `Co-Authored-By: Claude` trailer** in commits. (Maintainer preference; see `memory/feedback_no_coauthor_trailer.md`.)
- Squash on merge is fine — Netlify rebuilds preview per PR commit.
- Don't `git push --force` after review starts; force-pushes invalidate inline review comments.

---

## 10. Docusaurus features worth knowing

- **`<DocCardList>`** — renders category cards on landing pages; pulls title/description from frontmatter automatically.
- **Auto-generated sidebar** via `sidebars.js` — explicit is better than auto for docs that need careful ordering.
- **Search** — built-in local search via `@easyops-cn/docusaurus-search-local` is plenty for small sites; Algolia DocSearch for larger.
- **Light/dark mode** — default in Docusaurus 3; you can wire a brand-specific palette in `docusaurus.config.js > themeConfig.colorMode`.
- **Mermaid** — `@docusaurus/theme-mermaid` + `markdown.mermaid: true`.
- **Admonitions** — built in, no plugin required.
- **MDX** — `.mdx` extension instead of `.md` to embed React components. Use for landing pages with cards; plain `.md` for everything else.
- **i18n** — supported but high-cost; don't enable unless you have translators.

---

## 11. When docs and code diverge

The chart (or whatever's being documented) is the source of truth. If a
doc says one thing and the code does another:

- Code correct, doc stale → fix the doc.
- Doc captures intended behavior, code has a bug → file a code issue and fix the code. Leave a TODO in the doc only if absolutely necessary — and remove it as soon as the code lands.

Never "let the doc be aspirational" with the expectation that the code
will catch up. It won't, and the doc will mislead readers. Truth-forks
are how documentation becomes worthless.

---

## 12. Self-critique pass (the single highest-leverage habit)

Before opening the PR, read the diff *as the reviewer*, not as the
author. Different mode. You'll catch:

- Audience drift mid-section
- Claims you didn't verify against the code
- Sentences that read fine in your head but parse weirdly cold
- Duplication with other pages
- Stale literals you didn't realize you typed
- TODO leaks
- Awkward modifiers from copy-edits

If you have access to a `/code-review` or `/review` automation, run it on
the diff before pushing. The author-vs-reviewer mode shift is real;
catch the easy stuff before a human reviewer has to.
