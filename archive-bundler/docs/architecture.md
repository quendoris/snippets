# Architecture

## Goal

`archive-bundler` turns a file selection into a self-describing archive rather than treating ZIP creation as an opaque packaging step.

The data flow is:

```text
base + sources + excludes + metadata
        ↓
validate selection boundary
        ↓
stable repository-relative file list
        ↓
first-pass inventory (size + SHA-256)
        ↓
deterministic manifest + summary
        ↓
second-pass read + integrity recheck
        ↓
normalized ZIP entries
        ↓
fsync temporary archive
        ↓
os.replace() destination
```

## Selection boundary

`--base` defines the naming/security root.

Every selected source must resolve below that root. Archive member names are always derived from paths relative to `--base`; absolute host paths are not written into the bundle manifest.

Relative source arguments are interpreted relative to `--base`, not the caller's current directory once the base is known.

## Symlink policy

v0.1 rejects symlink sources and symlink entries.

This intentionally avoids several ambiguities:

- whether to archive the link or target bytes;
- whether a link can escape the declared base;
- platform-dependent ZIP symlink metadata;
- mismatch between provenance path and actual byte source.

A future symlink mode must be explicit rather than changing this behavior silently.

## Inventory-before-publication

The first pass reads every selected file and records:

- repository-relative path;
- byte length;
- SHA-256.

The second pass reads the file again immediately before adding it to the archive. If either size or SHA-256 differs, bundling aborts.

This creates a narrow consistency check against sources changing between manifest creation and archive publication.

It is not a filesystem snapshot: coordinated modifications can still occur outside the exact reads, and no OS-level snapshot/locking API is used.

## Deterministic archive representation

Source entries and generated evidence use a normalized `ZipInfo`:

- fixed timestamp: `1980-01-01 00:00:00`;
- storage method: `ZIP_STORED`;
- Unix regular-file mode: `0644`;
- UTF-8 filename flag;
- sorted member names.

No implicit current timestamp is placed in manifest or summary.

The design favors reproducibility over compression ratio. Compression can introduce library/version-dependent byte differences and is deliberately absent from the v0.1 contract.

## Generated evidence namespace

`_bundle/` is reserved inside the archive.

Generated files are:

```text
_bundle/manifest.json
_bundle/summary.md
```

A source path under `_bundle/` is rejected to prevent collision or ambiguity between generated evidence and user input.

## Atomic publication boundary

The archive is created as a temporary file in the destination directory. After `zipfile.ZipFile` closes, the temporary file is fsynced and published with `os.replace()`.

The publication unit is therefore one archive file.

This does not make the source inventory atomic and does not fsync the destination directory itself.

## Manifest determinism

The JSON manifest uses:

- sorted metadata keys;
- stable file order;
- `sort_keys=True` serialization;
- no generated wall-clock value.

The absolute destination path and final archive SHA-256 are returned to the caller after publication but are not embedded in the bundle, avoiding a self-referential archive hash and host-path-dependent archive bytes.
