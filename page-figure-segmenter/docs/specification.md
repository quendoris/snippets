# Proposed specification

This file describes the contract the reusable snippet is expected to expose **after** the project-local algorithm is validated. It is not yet an implementation guarantee.

## Input

One raster page image plus optional provenance metadata.

Required semantic input:

- decoded image pixels in a supported 8-bit or losslessly normalized luminance/color representation.

Optional caller metadata:

- source identifier;
- source SHA-256;
- source-page index;
- caller-defined tags used only for reporting/stratification.

No OCR text, caption text, language model result, or semantic figure label is required for segmentation.

## Processing contract

The implementation is expected to perform these stages explicitly and report their status:

1. page-type assessment;
2. local paper/ink response estimation;
3. connected-component extraction;
4. page-local text scale estimation (`H_cap`, `W_stroke`);
5. local text-likeness estimation;
6. statistically strong seed selection;
7. bounded multi-source geodesic component growth;
8. candidate-region filtering/grouping;
9. closure-cost evaluation and optional interior fill;
10. page-relative outer margin;
11. hard/soft alpha-mask construction;
12. structured evidence export.

A stage may decline to produce a figure region. Returning "no accepted regions" is a valid result and must not be treated as an implementation failure.

## Page-type outcome

At minimum the result should distinguish:

- `normal-text-page` — page-local text-scale model is applicable;
- `unsupported-or-nontext-page` — page is cover-like, full-tone, nearly blank, or otherwise outside the calibrated text-page model;
- `scale-estimation-failed` — page looked applicable but no stable text scale could be estimated.

The exact taxonomy may change during validation, but unsupported inputs must fail closed rather than producing confident arbitrary masks.

## Region output

Each accepted region should expose at least:

- stable region id within the page result;
- source-coordinate bounding box;
- hard binary support mask or a deterministic encoding/reference to it;
- soft alpha mask or deterministic parameters used to derive it;
- seed component ids and seed scores;
- normalized region evidence (area, extent, continuity or later validated equivalents);
- mean/max text-likeness intrusion evidence;
- closure decision and closure cost;
- segmentation confidence or, preferably, the measurable quantities from which caller policy can derive one;
- model/parameter-set version.

## Page output

A page-level machine-readable result should include:

- schema/version;
- input dimensions;
- optional caller provenance copied verbatim;
- page-type classification and observables;
- `H_cap` and `W_stroke` when available;
- foreground/threshold methodology identifiers;
- seed false-positive budget or calibrated seed criterion;
- graph/growth coefficients;
- accepted and rejected candidate-region summaries;
- diagnostics/failure reasons;
- deterministic output artifact paths when using a CLI.

## Rendering output

The reusable segmenter should keep segmentation and archival rendering separable. A CLI may optionally provide a reference renderer that emits:

- lossless PNG with alpha;
- hard mask;
- soft alpha mask;
- debug overlay;
- JSON report.

If desaturation is enabled, it must preserve source luminance. Whitening, inpainting, redrawing, denoising of historical strokes, or arbitrary background replacement are outside the default archival contract.

## Parameterization

All geometry that controls segmentation must be dimensionless or derived from measured page scale. Examples:

- gap radius / `W_stroke`;
- margin / `W_stroke`;
- alpha feather width / `W_stroke`;
- component height / `H_cap`;
- component area / (`H_cap·W_stroke`).

Absolute-pixel emergency limits may exist only for decoder safety or degenerate-input protection and must not define ordinary segmentation behavior.

## Determinism

For fixed:

- source pixels;
- implementation version;
- dependency versions where numerically relevant;
- model/parameter-set version;
- CLI/API arguments;

the segmenter should produce identical region decisions and masks. If any stage becomes stochastic during later research, an explicit seed and reproducibility policy becomes mandatory.

## Exit/failure semantics for the eventual CLI

Proposed behavior:

- exit `0`: input processed successfully, including the valid case of zero accepted figures;
- non-zero: invalid/unreadable input, unsupported requested mode, corrupted parameter set, internal invariant failure, or requested artifact publication failure.

Page-level non-applicability should normally be represented in the JSON result rather than crashing a multi-page batch.

## Calibration contract

A fitted parameter set is not called validated unless its provenance records:

- training/calibration page ids or dataset version;
- held-out validation page ids or dataset version;
- reference-mask protocol;
- declared loss terms and weights;
- aggregate and per-failure-class metrics;
- parameter uncertainty/stability analysis;
- known failure examples.

Caption/OCR metadata may stratify the dataset and verify expected figure presence, but it may not enter the image-to-mask computation unless a future separately named semantic mode explicitly changes the contract.