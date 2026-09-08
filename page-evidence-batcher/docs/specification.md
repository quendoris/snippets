# Specification

## Runtime

Python 3.10+ standard library only. No network access is required.

## Selection

`--start` is the value of the configured sequence field (`--index-field`, default `physical_index`), not an array offset. The exporter selects successive integer indices from `start` through `start + count - 1`.

If the first requested index is absent, the command fails. If a later index is absent, selection stops at the last contiguous record. Duplicate sequence indices are rejected.

## Required record data

By default each selected record needs:

- `id`: page identifier;
- `physical_index`: integer sequence index;
- `path`: source page path;
- `sha256`: optional expected source SHA-256.

The field names are configurable with `--id-field`, `--index-field`, `--source-field`, and `--sha256-field`.

IDs may contain only ASCII letters, digits, `.`, `_`, and `-`; path separators are rejected.

Relative source paths are resolved below `--source-base`.

## Evidence

`--evidence NAME=PATH_TEMPLATE` is repeatable. `PATH_TEMPLATE` is formatted from the current record. For example:

```text
--evidence kraken=corpus/ocr/raw/kraken/{id}.txt
```

Relative evidence paths are resolved below `--evidence-base`.

Evidence names must be unique safe identifiers. Every declared evidence layer must exist for every exported page.

## Preflight invariants

Before publication:

- every page ID is valid and unique;
- every selected index is unique;
- every source/evidence input exists, is a regular file, and is not a symlink;
- source SHA-256 is recomputed;
- when the configured SHA field has a non-null value, it must equal the recomputed digest.

Any failure exits with code `2` and does not publish a new partial batch.

## Output directory

For prefix `page-evidence` and pages 21 through 40:

```text
page-evidence-0021-0040/
├── README.txt
├── manifest.json
├── pages/
└── evidence/
    ├── <name-a>/
    └── <name-b>/
```

Evidence files retain their source suffix. Source pages retain their source suffix.

## Output manifest

Schema identifier: `page-evidence-batcher-v1`.

Each record contains:

- `id`;
- normalized `index`;
- recomputed `source_sha256`;
- relative `page_file`;
- map of evidence name to relative evidence path;
- `metadata`, populated from repeated `--carry-field` arguments.

The manifest does not declare an evidence layer canonical.

## Archive reproducibility

The `.tar.gz` archive is deterministic for identical input bytes and arguments:

- members are sorted;
- tar mtime is `0`;
- uid/gid are `0`;
- user/group names are empty;
- regular-file mode is `0644`;
- directory mode is `0755`;
- gzip mtime is `0`;
- the gzip header carries no filename.

The separately published directory contains ordinary filesystem metadata and is not itself byte-reproducible as a metadata object; only its file contents and structure are specified.

## Exit codes

- `0`: batch successfully published;
- `2`: contract/input failure reported by the snippet;
- argparse uses its normal non-zero exit behavior for malformed CLI syntax.
