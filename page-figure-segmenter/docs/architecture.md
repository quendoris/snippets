# Architecture

## 1. Boundary of the reusable unit

The snippet accepts a scanned page image and estimates one or more illustration assets together with auditable geometry/masks. It owns page-local measurement, seed evidence, graph growth, asset grouping, renderable-support masks and alpha geometry. It does **not** own OCR, semantic figure recognition, book-specific caption parsing, exercise schemas or publication layout.

The source image is immutable evidence. Every derived asset is described in source-page coordinates so a caller can regenerate or audit it.

This architecture is axiom-first: failed exploratory behavior has no compatibility status. If an implementation contradicts the invariants below, the implementation is replaced rather than the invariant weakened to protect legacy code.

## 2. Core invariants

1. **No fixed pixel geometry.** Distances, gaps, margins and feather widths are expressed using page-derived scale observables.
2. **Seeds are evidence, not assets.** A statistically non-text component establishes a starting point; it never receives final asset identity merely because it is a seed.
3. **Growth ownership is not rendering permission.** A component may be traversed by a graph path to establish connectivity without becoming opaque figure support.
4. **Asset grouping precedes crop emission.** Raw seed families are never exported directly as independent images. Nested, overlapping or otherwise strongly related families must first be resolved into asset candidates.
5. **Every asset owns its own support mask.** Cropping a page-wide union mask by an asset rectangle is forbidden because it can import support owned by another asset.
6. **Ordinary text is expensive to traverse and harder still to render.** Nearby words or bleed-through may not become figure ink merely because growth reached them.
7. **Interior paper and observed ink are separate layers.** Justified enclosed paper is opaque even when it contains no foreground stroke; observed figure support remains a distinct mask.
8. **Interior fill must be justified.** Open drawings remain open unless closing observed contour gaps is sufficiently cheap.
9. **Source evidence and publication cleanup are separate derivatives.** A clean publication asset must never overwrite or masquerade as the evidence-preserving derivative.
10. **Only the outer alpha boundary is softened.** Historical strokes themselves are not blurred as part of extraction.
11. **Page classification precedes text-scale estimation.** Inputs outside the calibrated body-page domain must fail closed or use a separately calibrated mode.
12. **No probability claim without a supported probability model.** Robust scores may rank outliers, but a Gaussian tail, p-value or false-positive probability may not be inferred unless its assumptions are validated.

## 3. Page observables

Let `L(x,y)` be source luminance and `B(x,y)` a slowly varying estimate of the local paper field. Define local ink response

`I(x,y) = max(B(x,y) - L(x,y), 0)`.

A foreground-support mask is derived from `I`. Connected components retain at least:

- bounding-box width `w(c)` and height `h(c)`;
- foreground area `A(c)`;
- spatial extent `e(c) = max(w(c), h(c))`;
- centroid and source-page position;
- local stroke-width evidence;
- neighborhood relations.

The high-confidence text population estimates two page-local units:

- `H_cap`: robust characteristic full-height text/capital scale;
- `W_stroke`: robust characteristic printed-stroke width.

These observables are measured per page and are not assumed constant across scans, resolutions, books or rerendered pages.

### 3.1 Failure-resistant text-scale estimation

The estimator must reject dust and bleed-through fragments as candidate text modes. A viable architecture is:

1. classify page domain from global image statistics;
2. establish a scale-relative dust floor;
3. score candidate component-height modes using both frequency and line/baseline support;
4. estimate `H_cap` from the selected text band;
5. estimate `W_stroke` from distance-transform evidence inside high-confidence text components.

A raw mode over all connected-component heights is explicitly insufficient for degraded scans.

## 4. Text-likeness is local evidence

A component is not text merely because it has text-like dimensions; figure fragments can share the same dimensions as letters.

Define `T(c) ∈ [0,1]` from evidence such as:

- size similarity to the page text population;
- nearby components of similar height;
- baseline/horizontal alignment;
- bilateral neighbors;
- repeated small gaps characteristic of words and lines.

`T(c)` has two distinct roles:

- a **growth/traversal penalty**;
- one input to the stricter **renderable-support decision**.

Those roles must not be collapsed. A graph may cross a dubious bridge without painting that bridge into the final PNG.

## 5. Strong seeds

For component `c`, a normalized feature vector may include

`f(c) = [log(h/H_cap), log(e/H_cap), log(A/(H_cap·W_stroke))]`.

Seed extremeness is evaluated relative to high-confidence text components, not every small component on the page. The reference distribution must therefore survive bleed-through and dust.

The default statistical interpretation is empirical/robust until a parametric distribution has been validated. Median/MAD, empirical tail quantiles or another declared robust outlier model are acceptable; an unsupported normal-tail conversion is not.

A strong seed combines extremeness with sufficiently low text-likeness. Border artifacts are treated separately rather than by a universal “thin line = not figure” rule because genuine ropes, poles and rails are also thin.

## 6. Component graph

Create graph `G=(V,E)` where nodes are foreground components and edges represent plausible normalized spatial continuation.

A provisional edge cost may be decomposed as

`C(u,v) = C_gap(u,v) + λ_text·T(v) + C_artifact(v) + C_context(u,v)`.

`C_gap` uses `W_stroke`/`H_cap`; other terms remain dimensionless calibration parameters.

Spatial indexing is an optimization only. It must not change graph semantics: candidate-neighbor discovery must be based on component support/bounding boxes, not merely centroid proximity, otherwise a long rail and a short fragment close to its endpoint can be missed despite having a small true geometric gap.

## 7. Multi-source geodesic growth

Run bounded multi-source shortest-path growth from accepted seeds.

Growth establishes **ownership/reachability**, not final support. It is permitted to cross a small amount of uncertain evidence when this is needed to connect a broken drawing. Repeated ordinary-text penalties must make paths into paragraphs progressively expensive.

Seed ownership is retained so collisions and ambiguous areas are explicit rather than silently merged.

## 8. Seed-family regions

Each seed owner yields an initial family/region. Region evidence can include:

- total normalized area;
- maximum extent;
- seed strength/count;
- continuity;
- fraction of text-like traversal;
- border contact.

Seed existence alone never implies asset acceptance.

## 9. Asset grouping

This is a separate stage from graph growth and support recovery.

Raw seed families are hypotheses. Before any crop is emitted, decide whether families are:

- different parts of the same illustration;
- duplicate/nested views of the same support;
- truly distinct neighboring illustrations.

Grouping may use intersection/nesting, normalized axis gaps, orthogonal overlap, continuation/orientation evidence and later calibrated structural evidence. It must be evaluated explicitly for false splits and false merges.

The output of this stage is the first object allowed to receive a stable **asset identity**.

## 10. Renderable support

For a grouped asset candidate, derive an asset-specific observed-support mask.

A component reachable during graph growth is included only when independent support evidence justifies rendering it. Examples of reasons to retain support include:

- membership in a strong seed/core;
- sufficiently large/extended figure-like geometry;
- close support continuity to the core;
- validated orientation/stroke continuation.

Examples of reasons to omit support include:

- isolated normal-sized glyph geometry outside the figure core;
- high text-likeness reached only as a bridge;
- weak bleed-through fragments with no structural support;
- page-edge artifacts.

This stage is what prevents “the algorithm crossed the letter, therefore the letter appears in the PNG.”

## 11. Closure and interior paper

The intuitive “mostly enclosed” idea is represented as a closure-cost problem.

For an asset-specific support mask:

1. provisionally close only small scale-relative gaps;
2. flood-fill from a guaranteed exterior (use a padded exterior, not an unverified source corner);
3. identify candidate enclosed paper;
4. measure artificial bridge support/topology required to create that enclosure;
5. accept interior only below a calibrated closure budget.

Observed ink support and accepted interior paper remain separate masks. Interior paper may be opaque even though it is not figure ink.

## 12. Margin and alpha

Combine observed support with justified interior, then add a small scale-relative margin such as

`r_margin = k_margin·W_stroke`.

Construct outer alpha feather over

`r_alpha = k_alpha·W_stroke`.

The interior remains opaque. Feathering acts on the outer mask boundary only.

## 13. Evidence-preserving versus clean rendering

A robust implementation should be able to emit at least two derivatives from the same geometry.

### 13.1 Source-preserving derivative

- grayscale/desaturated source pixels;
- accepted alpha geometry;
- original source luminance retained for audit, including historical paper irregularity and any source contamination inside the accepted region.

### 13.2 Publication-clean derivative

- observed figure strokes still come from source pixels;
- accepted paper-only interior may come from a slow local paper-field estimate `B(x,y)` rather than reverse-side text or unrelated foreground;
- no redrawing/sharpening/invented stroke content;
- same traceable source coordinates and masks.

The clean derivative is not evidence and must not replace the source-preserving derivative.

## 14. Calibration model

A parameter vector `θ` contains global dimensionless coefficients: seed criterion, text penalty, growth budget, grouping limits, support criteria, closure scale/budget, margin scale, alpha width and any validated context terms.

Optimization requires independent ground truth. A representative pilot must include manual source-coordinate masks/regions and difficult negatives. One possible declared loss is

`L(θ) = λ_miss E_missed_stroke + λ_text E_text_intrusion + λ_boundary E_boundary + λ_merge E_false_merge + λ_split E_false_split + λ_fp E_false_figure + λ_fill E_false_fill`.

Calibration and held-out validation must be separate. Caption count or successful visual examples are QA signals, not a substitute for mask-level validation.

## 15. Evidence and reproducibility

For each processed page/asset the implementation should be able to emit:

- page-domain decision and observables;
- `H_cap`, `W_stroke`;
- component evidence or reproducible digest;
- seed list/scores and statistical method;
- text-likeness;
- graph/growth parameters;
- raw seed-family identities;
- grouping decisions;
- asset-specific observed-support mask;
- closure/interior mask and cost;
- hard/soft alpha;
- source bounding box;
- source-preserving and clean derivative metadata;
- debug overlays;
- source SHA-256 when supplied/available.

The same source bytes, implementation version and frozen parameter set should produce the same outputs.
