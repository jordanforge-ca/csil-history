# documents/

Host source files here only when **redistribution is clearly permitted**.

This folder is intentionally almost empty. The default for copyrighted or un-cleared historical material is:

1. A metadata / annotation page under `sources/`
2. A bibliographic citation in `references.bib`
3. A stable public link (`external_url`)
4. An archived-link field when an archive copy already exists (`archived_url`)

## When a file may be added

A file may be committed here only if at least one of the following is documented on the matching source page and in a `rights_note`:

- the work is in the public domain
- the copyright holder has given written permission to redistribute this copy
- a licence on the work expressly allows redistribution of the file we are hosting
- a government or Crown copyright notice clearly permits this reproduction

“I found a PDF on the web” is not permission. Neither is the repository’s CC BY 4.0 license.

## When a file must not be added

- private CSIL employer records
- personal health information
- unpublished private correspondence
- material from private chats or private repositories
- scans whose rights are unknown
- copies that an archive or library has restricted

## How to add a permitted file

1. Confirm rights in writing and quote the permission or licence on the source page.
2. Use a stable, descriptive filename (for example `1987-creekview-202-evaluation.pdf`).
3. Set `document_path` and `availability: full-text-public` (or `permission-required` if the page may describe the file but not offer an open download).
4. Do not rely on Git LFS unless the project later standardises on it.

See [docs/copyright-policy.qmd](../docs/copyright-policy.qmd).
