# Page Evidence Batcher

Build a portable review batch from a contiguous sequence of page records, copying each source page together with any number of page-aligned evidence files.

The snippet was extracted from the editorial export workflow used by `corpus-motuum`, but the reusable implementation does not know about that repository, OCR engines, book schemas, or canonical-text policy.

## Example

```bash
python src/page_evidence_batcher.py \
  --manifest corpus/source/page-manifest.json \
  --start 261 \
  --count 20 \
  --source-base . \
  --evidence rus=corpus/ocr/raw/rus/{id}.txt \
  --evidence orus=corpus/ocr/raw/orus/{id}.txt \
  --evidence kraken=corpus/ocr/raw/kraken/{id}.txt \
  --carry-field source_pdf_sheet \
  --carry-field spread_side \
  --out-dir work/editorial-batches \
  --name-prefix editorial
```

The command publishes both `editorial-0261-0280/` and `editorial-0261-0280.tar.gz`.

## Contract

The input manifest must contain an array of page-like objects. Field names for page ID, sequence index, source path and source SHA-256 are configurable. Evidence inputs are repeatable `NAME=PATH_TEMPLATE` arguments; templates may reference fields in each page record with Python format syntax such as `{id}`.

Before publishing anything, the exporter verifies that every selected source/evidence path exists, is a regular non-symlink file, page IDs are safe filenames, page indices are unique and contiguous across the selected range, and declared source hashes match actual bytes when present.

The generated tarball normalizes member order, timestamps, ownership and modes and fixes the gzip timestamp, so identical inputs and arguments produce identical archive bytes.

See `docs/specification.md` for the exact format and exit behavior.
