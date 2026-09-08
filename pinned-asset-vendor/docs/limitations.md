# Limitations

## Pinning is caller-owned

The runner verifies the bytes named by the manifest, but it cannot prove that a URL is immutable. For reproducible vendoring, use source URLs bound to an immutable content identity such as an exact Git commit or content-addressed object.

## No version discovery

There is no `latest`, tag resolution, release API lookup, mirror selection or dependency solver. Updating an asset is an explicit manifest change.

## HTTPS transport is necessary but not sufficient

The downloader requires HTTPS and rejects a final non-HTTPS redirect. Trust still comes from expected byte identities, not from TLS alone.

## Whole-file memory use

Version `0.1.0` reads each downloaded and verified asset into memory as one `bytes` object. It is suitable for small and medium vendored assets, not multi-gigabyte datasets. Large resumable acquisition belongs in a streaming downloader with checkpoints, such as AERIS's dataset pipeline rather than this snippet.

## No resume

Interrupted downloads are not resumed. Temporary local publication is atomic, but network acquisition restarts on the next attempt.

## Serial processing

Assets are checked/vendored one at a time. No parallel fetch or bandwidth scheduling is implemented.

## Filesystem durability

The temporary file itself is flushed and `fsync()` is requested before replacement. Version `0.1.0` does not additionally `fsync()` the destination directory after `os.replace()`, so it does not claim crash-consistent directory-entry persistence across every operating system/filesystem.

## Existing incorrect destination

Vendor mode leaves an incorrect existing destination in place while downloading/verifying replacement bytes. It is replaced only after the new temporary file passes verification. Check mode never modifies it.

## License policy is external

The originating Persona Training Lab vendor had explicit Noto license handling. This generic snippet does not infer which assets are licenses or whether a project has redistribution rights. Legal/licensing policy remains the consuming project's responsibility.

## Git SHA-1 is optional evidence

Git blob SHA-1 support exists to reproduce useful provenance checks from Git-backed sources. It is not treated as the primary cryptographic integrity mechanism; SHA-256 is mandatory for every asset.
