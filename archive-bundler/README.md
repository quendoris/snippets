# Archive Bundler

`archive-bundler` collects an explicit set of files below a declared base directory and produces a deterministic ZIP bundle containing:

- the selected source files;
- `_bundle/manifest.json` with size and SHA-256 evidence;
- `_bundle/summary.md` with a human-readable inventory.

The snippet is intended for audit packages, documentation evidence, generated reports, handoff bundles, and other development artifacts where "zip this folder" is not enough provenance.

## Status

Experimental `0.1.0`.

## Requirements

- Python 3.11+;
- standard library only;
- no network access.

## Example

```bash
python archive-bundler/src/archive_bundler.py \
  artifacts/release-audit/run-001 \
  docs/report.md \
  --base /path/to/repository \
  --output /tmp/release-evidence.zip \
  --metadata commit=abc123 \
  --metadata purpose=release-audit
```

JSON result:

```bash
python archive-bundler/src/archive_bundler.py artifacts \
  --base . \
  --output bundle.zip \
  --json
```

Exclude repository-relative paths with repeatable globs:

```bash
--exclude "artifacts/**/*.tmp" --exclude "**/.DS_Store"
```

## Determinism

Archive entries are:

- sorted by repository-relative path;
- written with a fixed ZIP timestamp (`1980-01-01 00:00:00`);
- written as regular `0644` files;
- stored without compression (`ZIP_STORED`).

The manifest and summary contain no implicit wall-clock timestamp.

For unchanged source bytes, the same selected paths and the same user metadata should therefore produce identical archive bytes on supported Python implementations/platforms. The returned result payload can include the absolute output path, but that path is **not written into the archive manifest**.

## Integrity behavior

The source inventory is hashed before archive creation. Each file is read again immediately before it is written; size and SHA-256 must still match the inventory. If a source changes during bundling, the temporary archive is rejected instead of publishing a manifest that describes different bytes.

Output is written to a temporary file in the destination directory and published with `os.replace()` after the ZIP is complete and fsynced.

## Safety boundaries

- every source must resolve below `--base`;
- symlink sources/entries are rejected in v0.1;
- `_bundle/` is a reserved archive namespace for generated evidence;
- an existing output file encountered inside a selected source tree is excluded from its own bundle;
- source files are read only; only the requested output path is written/replaced.

See [`docs/specification.md`](docs/specification.md) and [`docs/limitations.md`](docs/limitations.md) for exact semantics.
