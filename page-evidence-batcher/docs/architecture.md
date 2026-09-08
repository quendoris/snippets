# Architecture

## Responsibility

`page-evidence-batcher` owns one operation: turn a contiguous run of page records plus aligned evidence files into a portable review artifact.

It deliberately does not decide what the evidence means, which layer is authoritative, how review is performed, or how reviewed content is committed back into a source project.

## Data flow

```text
JSON manifest
    |
    v
record selection by explicit sequence index
    |
    +--> source page path ------> preflight + optional SHA-256 verification
    |
    +--> evidence templates ----> preflight aligned files
    |
    v
staging directory
    |
    +--> pages/
    +--> evidence/<name>/
    +--> manifest.json
    +--> README.txt
    |
    v
deterministic tar.gz
    |
    v
atomic publication into --out-dir
```

## Boundaries extracted from Corpus Motuum

The originating project script assumed:

- `records` under `corpus/source/page-manifest.json`;
- `physical_index` ordering;
- source paths stored in `path`;
- SHA-256 stored in `sha256`;
- exactly the OCR engines `rus`, `orus`, and `kraken`;
- evidence filenames of `<page-id>.txt`;
- an `editorial-*` output name;
- Corpus Motuum's batch schema and explanatory README.

The reusable snippet parameterizes the record/field names and evidence templates and emits its own project-neutral schema. The originating project can keep its wrapper and project-specific output schema until migration is deliberately chosen.

## Publication model

All input validation happens before output publication. Files are assembled in a temporary directory under the requested output directory. Only after the directory and deterministic archive have been built successfully are they moved to their final names.

Existing outputs with the same batch name are replaced only at this final publication stage.
