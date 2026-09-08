# Limitations

- The exporter models exactly one source asset per page record. Multi-file source pages require a different abstraction.
- Evidence alignment is filename/template based; the snippet does not inspect semantic contents or prove that an evidence file really belongs to the page beyond the caller's template.
- Sequence indices must be integers and the selected batch is contiguous.
- Missing later indices shorten a batch rather than failing; callers that require exactly `--count` records must verify the emitted range/count.
- Source hashes are SHA-256 only. Evidence files are copied but are not individually hashed into the current manifest.
- Symlinks are rejected rather than dereferenced. This keeps publication behavior explicit and avoids packaging data from outside the intended tree.
- The snippet intentionally does not preserve source permissions, ownership, or timestamps in the archive.
- The output directory is replaced after successful staging, but replacing the directory and archive is two filesystem operations rather than a single transaction spanning both paths.
- The generic output schema is not a drop-in replacement for project-specific editorial manifests. Originating projects should keep their local composition layer until they intentionally migrate.
