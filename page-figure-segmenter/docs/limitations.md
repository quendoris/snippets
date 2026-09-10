# Limitations and validation gates

This candidate is intentionally not yet a registered runnable snippet. The architecture is plausible and has encouraging project-local pilot behavior, but several failure classes must be measured before a reusable implementation is published here.

## Known unresolved cases

### Dark/full-tone pages

A text-scale model is meaningless on cover-like pages whose background is predominantly dark or textured. Such pages must be classified before text-scale estimation and should fail closed or enter a separately calibrated mode.

### Bleed-through / show-through

Old paper can expose reverse-side printing as thousands of small foreground fragments. Two distinct failures are possible:

- the fragment population corrupts the estimated text scale;
- isolated artifacts become statistically unusual false seeds.

The current architectural response is to derive the scale from line-supported text components and to filter grown seed families using area/extent/support evidence. This still requires held-out validation.

### Figure touching text

A figure may physically approach or touch a neighboring letter. Pure connected-component membership can therefore join illustration and text. The graph-growth model must prove that local text penalties stop propagation without cutting authentic strokes.

### Thin apparatus lines

Ropes, poles, ladder rails, bars and similar geometry may have low foreground area despite large extent. Region filtering cannot require a large area alone.

### Open drawings

Not every illustration has a closed contour. Interior filling must be optional and closure-cost gated; otherwise large unrelated background areas can be invented.

### Multiple figures on one page

Separate illustrations may be close to each other, may share a caption zone, or may contain visually similar support lines. Seed ownership and region grouping must be validated against both false merges and false splits.

### Captions and headings

Large capital letters or short headings can be statistical outliers relative to ordinary body text. Seed selection therefore needs local text-likeness/context evidence in addition to size/area extremeness.

### Page-edge artifacts

Binding shadows, crop borders, scanner edges and stains can create very large connected components. Border proximity and page-type evidence must prevent these from becoming ordinary figure seeds.

### Weak historical strokes

Raising the foreground threshold can suppress bleed-through but may also destroy the very faint strokes the archival workflow is intended to preserve. A likely solution is separate **strong seed evidence** and **weaker growth support**, but that two-threshold contract must be measured before it is frozen.

## Validation gates before adding `snippet.toml` and reusable source

The draft should not be promoted to an actual snippet until all of the following are true:

1. A manually reviewed reference set contains representative positive figures and negative pages, not only caption-selected positives.
2. The set explicitly includes dark/non-text pages, bleed-through, thin lines, open drawings, multiple figures, page-edge artifacts, and figure/text contact.
3. Reference masks or equivalent source-coordinate annotations exist for the cases used to tune geometry.
4. Calibration pages and held-out validation pages are separated.
5. False figure detection, missed-stroke, text-intrusion, false-merge and false-split behavior are reported separately.
6. The algorithm does not use OCR/canonical/caption text to construct its segmentation mask.
7. The page-type detector fails closed on uncalibrated full-tone inputs.
8. All ordinary geometric decisions are scale-relative rather than fixed-pixel constants.
9. Final archival rendering preserves source luminance and softens only the outer alpha boundary.
10. Debug/evidence outputs make every surprising region auditable.
11. Repeated runs with the same source/model version are deterministic.
12. A project-local full-corpus dry run is manually sampled before any claim of production suitability.

## What success does not mean

High performance on one historical book does not prove universality across newspapers, photographs, halftones, handwritten marginalia, colored illustrations, mathematical diagrams, or modern page layouts. The reusable snippet must publish the domain on which its parameters were calibrated.

A model tuned for archival preservation may also intentionally prefer a small amount of extra local paper context over clipping a faint stroke. That tradeoff is policy and must be visible in the loss weights/parameter-set provenance rather than hidden in code.

## Security and privacy

The intended algorithm is local and does not require a network connection. If future integrations upload pages for OCR, semantic classification or remote optimization, that behavior belongs outside this snippet or must be explicitly declared as a different mode.