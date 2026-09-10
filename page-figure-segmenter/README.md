# Page Figure Segmenter

**Status: architecture draft; not yet a registered runnable snippet.**

This candidate snippet is being distilled from the figure-extraction work in `quendoris/corpus-motuum`. It targets a narrow engineering problem: segment printed illustrations from scanned text pages without relying on fixed pixel thresholds and without silently destroying weak strokes, paper luminance variation, or other source evidence inside the accepted figure region.

The reusable design is intentionally separated from Corpus Motuum-specific concepts. It does not know about exercise numbers, Russian text, `N ФИГ.` captions, book schemas, page numbering, or canonical transcription. Text/caption metadata may be used by a caller to construct a calibration set, but it must not determine the segmentation mask.

The intended output is a provenance-rich figure region and alpha mask. A caller may then create an archival PNG, a debug overlay, or another derivative while retaining traceability to the immutable source page.

## Why this is still a draft

The architecture is being written down now so the important invariants do not get lost while the project-local algorithm is tested. The reusable implementation, `snippet.toml`, and contract tests will be added only after the algorithm has survived representative positive pages, negative controls, bleed-through, open drawings, thin apparatus lines, multiple figures on one page, and non-page/cover-like inputs.

This keeps the repository's extraction policy intact: real project need → working and measured project-local implementation → reusable core → independent tests and specification.

See:

- `docs/architecture.md` — scale model, seed model, graph growth, closure and alpha pipeline;
- `docs/specification.md` — proposed reusable contract and measurable outputs;
- `docs/limitations.md` — known unresolved cases and the validation gates required before implementation is published here.
