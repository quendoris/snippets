# Pinned Asset Vendor

Exact-byte HTTPS asset vendoring with an offline verification mode.

The snippet was distilled from Persona Training Lab's pinned Noto Arabic font vendor. The original script bound downloads to a fixed upstream commit and verified size plus Git blob identity before atomically publishing files. This reusable version removes font/repository/layout assumptions and makes each exact source URL and expected identity manifest data.

## Manifest

Example `assets.toml`:

```toml
schema = 1
user_agent = "example-project-asset-vendor/1"

[[asset]]
name = "schema fixture"
source_url = "https://raw.githubusercontent.com/example/project/0123456789abcdef/path/schema.json"
destination = "vendor/schema.json"
size = 1234
sha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
git_blob_sha1 = "0123456789abcdef0123456789abcdef01234567"
```

`git_blob_sha1` is optional. SHA-256 and exact byte size are mandatory.

## Vendor

```bash
python pinned-asset-vendor/src/pinned_asset_vendor.py \
  --root /path/to/project \
  --manifest assets.toml
```

An already-correct destination is not downloaded again. A missing or incorrect destination is downloaded to a temporary file in the destination directory, verified, flushed/fsynced, verified again from disk, and published with `os.replace()`.

## Offline check

```bash
python pinned-asset-vendor/src/pinned_asset_vendor.py \
  --root /path/to/project \
  --manifest assets.toml \
  --check
```

`--check` performs no network operation. Every listed destination must already exist and match the manifest.

## Machine-readable output

Add `--json` for a deterministic result payload containing the verified size, SHA-256, Git blob SHA-1 and action for every asset.

## Exit codes

- `0` — all assets verified/vendored;
- `1` — asset download/integrity/filesystem failure;
- `2` — invalid manifest or CLI configuration.

See `docs/specification.md`, `docs/architecture.md`, and `docs/limitations.md` for exact behavior.
