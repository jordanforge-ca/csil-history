# Contributing to the CSIL History Archive

Thank you for helping reconstruct a source-driven history of Choice in Supports for Independent Living (CSIL) in British Columbia.

This is a **digital-history / annotated-bibliography** project. Evidence comes before narrative. The public site should make it easy to inspect sources, see uncertainty, and add missing documents — not to campaign for a policy outcome.

## Before you add anything

This repository is public. Treat every commit as permanently published.

Do **not** add:

- private CSIL employer records
- personal health information
- unpublished private correspondence
- material from private chats or internal jordanforge repositories
- scans or PDFs unless redistribution is clearly permitted (see [docs/copyright-policy.qmd](docs/copyright-policy.qmd))

If you are unsure whether a file can be public, do not commit it. Open an issue describing the source without attaching the file.

## Editorial principles

### 1. Evidence before narrative

Every material historical claim should ultimately point to a source record. If you cannot cite a source, label the statement as an open question, a working research proposition, or an attributed recollection.

### 2. Prefer primary and near-primary sources

Use the `source_type` vocabulary in [docs/vocabularies.qmd](docs/vocabularies.qmd). Later summaries and advocacy writing can be catalogued as secondary sources; they should not silently become the voice of the archive.

### 3. Separate fact, attribution, and interpretation

On a page, keep these distinguishable:

| Kind | Use when |
| --- | --- |
| Documented fact | A cited source has been inspected, or a specific passage is quoted/paraphrased with a citation |
| Attribution | Someone said or wrote it; the archive is not independently asserting it |
| Interpretation | The archive or a later writer is inferring a relationship, cause, or meaning |
| Open question | The archive does not yet have enough evidence |

Do not collapse these into definitive prose.

### 4. Preserve disagreement

If sources conflict, show the conflict. A known example the site must accommodate is **1993 versus 1994** as a CSIL starting year. Do not pick a winner in narrative text until the evidence is inspected and the disagreement is still described.

### 5. No advocacy framing in the historical record

Current policy work may *link to* this archive. It must not determine historical conclusions, page tone, or what counts as a fact. Avoid campaign language, slogans, and implied policy recommendations on history, source, people, and timeline pages.

### 6. Accessible by default

The [accessibility baseline](docs/accessibility.qmd) is a merge blocker. In short:

- One `h1`; body headings start at `##` (no fake headings via bold or size)
- Skip link, landmarks, and current-page indication that is not colour alone
- Visible `:focus-visible` rings; do not remove outlines
- Usable at 200% zoom / ~320px; no sticky chrome covering text
- Comfortable default body text (18px / line-height 1.6; never under ~16px)
- Descriptive links; status as text, not colour only
- Real tables with captions and headers
- No unlabeled custom controls (site search is disabled on purpose)

**Blocker and High accessibility gaps must be fixed before merge.** See [docs/accessibility.qmd](docs/accessibility.qmd) and the overrides in `styles.scss`.

### 7. Respect living participants

Names in `people/` are stubs until a **cited** public source supports a statement.

Oral-history or personal contributions need:

- explicit permission to publish
- an agreed attribution line
- a record of what may and may not be published
- no contact with participants unless a separately agreed research protocol exists

This bootstrap does not authorise contacting historical participants.

## How to add a source

1. Copy [`sources/example-template-source-record.qmd`](sources/example-template-source-record.qmd).
2. Choose a stable filename and `id` (`src-...`).
3. Fill the front matter using only [controlled vocabulary](docs/vocabularies.qmd) values.
4. Set `verification_status` honestly. If you have not inspected the item, do not mark it `verified-inspected`.
5. Prefer a bibliographic citation and a stable public URL over uploading a file.
6. Add a matching entry to `references.bib` when useful.
7. Link the source from any history, person, organization, or timeline record that relies on it.
8. Open a pull request that says what was added and what remains uncertain.

Read [docs/source-metadata.qmd](docs/source-metadata.qmd) before inventing new fields.

## How to add a timeline event

Edit [`data/timeline.yml`](data/timeline.yml). That file is the structured source for [timeline.qmd](timeline.qmd). Include:

- a sortable `date`
- a human `date_display` (for example `c. 1985`)
- `date_precision` (`exact`, `approximate`, `contested`, or `unknown`)
- `confidence` from the evidence-status vocabulary
- associated source ids or a clear “none catalogued yet”
- notes for approximate or contested dates

Do not add a JavaScript timeline library.

## How to add a person or organization page

Create a stub first. Use the four person sections:

1. Documented role
2. Attributed recollection
3. Sources mentioning this person
4. Questions we would like to verify

Leave sections empty rather than guessing. Do not write a biography from memory.

## Pull requests

- Keep changes reviewable: one source, one person, or one focused documentation change.
- Quote or paraphrase only what you have seen.
- State when a date is approximate or contested.
- Run `quarto render` locally if you can.
- Run `python3 scripts/check_a11y.py _site` after rendering.

## Link-checking strategy

1. Prefer relative links for internal pages.
2. For external sources, record the URL you used and, when available, an archived URL field.
3. CI currently checks internal anchors and basic HTML accessibility; it does not fetch the live web.
4. Periodic manual or `lychee`/equivalent external link checks can be added later without changing the site stack.

## Questions

Open a GitHub issue on this repository. Describe the source or correction; do not attach files of uncertain rights.
