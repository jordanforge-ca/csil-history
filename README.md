# CSIL History Archive

Public source-driven history of **Choice in Supports for Independent Living (CSIL)** in British Columbia.

This repository is an **evidence archive first** and a website second: concise orientation pages, an annotated source catalogue, and a place to record uncertainty, disagreement, and missing documents. It is not an advocacy campaign site.

**Repository:** <https://github.com/jordanforge-ca/csil-history>

**Expected Pages URL:** <https://jordanforge-ca.github.io/csil-history/>

Pages will go live after a maintainer enables GitHub Pages with **Source: GitHub Actions** (Settings → Pages). The workflow is [`.github/workflows/pages.yml`](.github/workflows/pages.yml).

## What this project is

- A Quarto static site with structured source, person, organization, and timeline records.
- A research workspace for reconstructing CSIL's history from primary and near-primary sources.
- A public catalogue of documents that are known to exist but have not yet been recovered.

It does **not** currently contain a finished historical narrative, bulk-ingested PDFs, or private records.

## Local build

Install [Quarto](https://quarto.org/docs/get-started/) 1.5 or later, then from the repository root:

```bash
quarto preview    # local preview server
quarto render     # writes HTML to _site/
```

After a render, required accessibility baseline checks (Python 3 standard library only; merge blocker):

```bash
python3 scripts/check_a11y.py _site
```

More detail: [docs/local-build.qmd](docs/local-build.qmd).

## Information architecture

| Path | Role |
| --- | --- |
| `index.qmd` | Home: purpose, scope, how to help |
| `history/` | Cited chapters for Creekview, ECPM, CSIL design/pilot, and later evolution; origins/context is folded into Creekview |
| `timeline.qmd` + `data/timeline.yml` | Working timeline driven from structured data |
| `sources/` | Annotated source records, including one labelled example |
| `people/` | Name stubs only until cited evidence exists |
| `organizations/` | Directory for organizations named in public sources |
| `research/wanted-sources.qmd` | Known-to-exist documents still being sought |
| `documents/` | Hosted files only when redistribution is clearly permitted |
| `docs/` | Metadata schema, vocabularies, copyright, accessibility |
| `references.bib` | Shared bibliography |

## Editorial rules (short)

1. Evidence before narrative.
2. Prefer primary and near-primary sources.
3. Separate fact, attribution, and interpretation.
4. Preserve disagreement; do not silently reconcile conflicting dates.
5. No advocacy framing in the historical record.
6. Accessible by default.
7. Respect living participants; do not publish private or health information.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Original site and repository content is [CC BY 4.0](LICENSE).

**Historical source documents do not inherit that license.** Default to citation plus a stable public link. Only add files under `documents/` when redistribution is clearly permitted. See [docs/copyright-policy.qmd](docs/copyright-policy.qmd).

## Commissioning context

This public archive was bootstrapped from [jordanforge-infrastructure#10](https://github.com/jordanforge-ca/jordanforge-infrastructure/issues/10). That issue is product/design context only. Do not copy private material from other jordanforge repositories into this one.
