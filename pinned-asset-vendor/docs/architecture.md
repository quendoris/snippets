# Architecture

## Boundary

The snippet owns one narrow transition:

```text
manifest identity
      +
HTTPS source bytes
      ↓
verify exact bytes
      ↓
atomic local destination
```

It does not choose versions, discover latest releases, resolve dependency graphs, install packages, or interpret asset contents.

## Manifest as the trust input

Every asset declares an exact HTTPS URL, destination, byte size and SHA-256. An optional Git blob SHA-1 can add evidence when the source is a Git object exposed through a raw-content endpoint.

The URL is deliberately full rather than synthesized from repository/branch fields. Immutability is therefore a property the caller must establish when writing the manifest — commonly by embedding an exact commit in the URL.

## Verification order

Downloaded bytes are checked in this order:

1. exact byte length;
2. SHA-256;
3. optional Git blob SHA-1.

The same verifier is used for existing destinations, downloaded response bytes and the temporary file after writing it to disk.

## Publication

A new asset is written to a unique temporary file in the destination directory. The file is flushed and `fsync()` is requested, then bytes are read back and verified. `os.replace()` publishes the verified temporary file to the declared destination.

Keeping the temporary file in the same directory makes the final replacement operate within one filesystem namespace on normal filesystems.

## Existing correct assets

Vendor mode first verifies an existing destination. If it already matches the manifest, no network request occurs and the result action is `already-verified`.

This makes repeated vendoring cheap while preserving exact-byte verification.

## Offline mode

`--check` calls only the local verifier. The network download function is outside that path entirely. A missing asset is a failure rather than a reason to acquire it.

## Path boundary

Destinations are POSIX-style relative paths. Absolute paths, parent traversal, `.` components and backslash spellings are rejected by manifest validation. The caller's `--root` is the publication boundary.
