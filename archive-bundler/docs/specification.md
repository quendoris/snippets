# Specification

## Invocation

```text
python src/archive_bundler.py SOURCE [SOURCE ...] --base BASE --output FILE [options]
```

Options:

- `--exclude GLOB` — repeatable repository-relative exclusion pattern;
- `--metadata KEY=VALUE` — repeatable manifest metadata entry;
- `--json` — print the result payload as JSON.

## Path resolution

`BASE` is expanded/resolved first.

A relative `SOURCE` is interpreted as:

```text
BASE / SOURCE
```

An absolute `SOURCE` is accepted only when its resolved path remains below `BASE`.

The output path is independent of `BASE` and may be outside it.

## Selection

A source may be a file or directory.

Directory sources are traversed recursively. Final selected files are deduplicated by their POSIX-style path relative to `BASE` and sorted lexicographically.

A file is excluded when any `--exclude` glob matches its base-relative path.

If the output archive already exists inside a selected tree, that exact output path is omitted so the bundle does not recursively include its previous version.

## Reserved namespace

Source members whose base-relative path starts with:

```text
_bundle/
```

are rejected.

The generated archive owns:

```text
_bundle/manifest.json
_bundle/summary.md
```

## Manifest schema

Current schema:

```json
{
  "schema": 1,
  "generator": "archive-bundler/0.1.0",
  "metadata": {},
  "totals": {
    "files": 0,
    "bytes": 0
  },
  "files": []
}
```

Each file record contains:

```json
{
  "path": "reports/result.json",
  "size": 1234,
  "sha256": "..."
}
```

`files` is sorted by `path`.

The manifest intentionally does not contain:

- host absolute paths;
- an implicit current timestamp;
- the final archive hash;
- the temporary output path.

## Metadata

`--metadata` accepts unique keys only.

Example:

```text
--metadata commit=abc123 --metadata locale=ru-RU
```

Metadata values are strings.

Duplicate keys and malformed entries without `=` are configuration errors.

## Summary

`_bundle/summary.md` contains:

- generator identity;
- file/byte totals;
- sorted user metadata;
- one table row per source file with size and SHA-256.

It is derived from the same inventory used to build `manifest.json`.

## ZIP member metadata

Every member uses:

```text
date_time      = 1980-01-01 00:00:00
compression    = ZIP_STORED
create_system  = Unix (3)
mode           = regular file 0644
UTF-8 flag     = enabled
```

No directory entries are written.

## Source-change check

Before archive construction, every source file is read to create its `FileRecord`.

Immediately before writing each source member, the file is read again. The second read must match both:

- `size`;
- `sha256`.

Mismatch raises `BundleError` and the destination is not replaced by the incomplete temporary archive.

## Publication

The output parent directory is created when necessary.

A temporary file is created in that same directory, written as the complete ZIP, fsynced, and then published through:

```python
os.replace(temp_path, output)
```

The temporary path is cleaned in a `finally` block when still present.

## Result payload

The in-memory/`--json` result extends the manifest-shaped data with:

```json
"archive": {
  "path": "/absolute/output.zip",
  "bytes": 9999,
  "sha256": "..."
}
```

This `archive` object is not embedded into `_bundle/manifest.json`.

## Exit behavior

- `0` — bundle published successfully;
- `1` — uncategorized OS/I/O failure caught by the CLI boundary;
- `2` — selection/metadata/configuration failure represented as `BundleError`.

## Read/write boundary

The selected sources are only read.

The snippet may create the output parent directory and replaces only the requested output file after successful temporary creation.
