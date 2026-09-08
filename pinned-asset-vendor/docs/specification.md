# Specification

## Runtime

Python 3.11+ using only the standard library.

## CLI

Required:

- `--manifest PATH` — TOML asset manifest.

Optional:

- `--root PATH` — destination root; defaults to current working directory;
- `--check` — offline verification only;
- `--timeout SECONDS` — positive network timeout, default `60`;
- `--json` — machine-readable output.

Relative manifest paths resolve below `--root`.

## Manifest schema 1

Top level:

- `schema = 1` — required;
- `user_agent` — optional non-empty string, default `pinned-asset-vendor/0.1`;
- one or more `[[asset]]` entries.

Each asset requires:

- `name` — unique non-empty display identifier;
- `source_url` — absolute HTTPS URL without embedded credentials;
- `destination` — unique POSIX-style relative path below `--root`;
- `size` — integer >= 0;
- `sha256` — lowercase 64-character hexadecimal digest.

Optional:

- `git_blob_sha1` — lowercase 40-character hexadecimal Git blob digest.

Duplicate names and duplicate destinations are rejected.

## Destination path validation

A destination is rejected when it:

- is empty;
- contains backslashes;
- is absolute;
- contains `.` or `..` path components.

## Byte identity

Verification requires exact size and SHA-256 equality. When `git_blob_sha1` is declared, the Git blob digest is computed as:

```text
SHA1("blob " + decimal-byte-length + NUL + bytes)
```

and must also match.

Git SHA-1 is supplementary provenance evidence; SHA-256 remains mandatory.

## Vendor mode

For each asset in manifest order:

1. if destination exists and verifies, emit `already-verified` and do not download;
2. otherwise fetch the exact HTTPS URL;
3. reject a final redirect URL whose scheme is not HTTPS;
4. verify response bytes;
5. create destination parent directories;
6. create a unique temporary file in the destination directory;
7. write, flush and `fsync()` the temporary file;
8. reread and verify temporary bytes;
9. publish with `os.replace()`;
10. remove leftover temporary file on failure.

Assets are processed serially.

## Check mode

For each asset in manifest order, read the declared destination and run the exact byte verifier. No download function is called.

## JSON result

Successful output contains:

- `passed: true`;
- `mode`: `vendor` or `check`;
- `asset_count`;
- ordered asset records containing name, destination, size, SHA-256, computed Git blob SHA-1 and action.

Failures in `--json` mode emit `passed: false` and an error string.

## Exit status

- `0`: all assets succeeded;
- `1`: acquisition, integrity or filesystem failure;
- `2`: manifest/CLI configuration failure.
