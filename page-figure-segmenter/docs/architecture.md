# Architecture

## 1. Boundary of the reusable unit

The snippet accepts a scanned page image and estimates one or more illustration regions. It owns segmentation geometry and confidence/evidence. It does **not** own OCR, semantic figure recognition, book-specific caption parsing, page-number interpretation, exercise schemas, or publication layout.

The source image is immutable evidence. Every derived region is described in source-page coordinates so a caller can regenerate or audit every output.

## 2. Core invariants

1. **No fixed pixel geometry.** Distances, gap tolerances, margins and feather widths are expressed using page-derived scale observables.
2. **Seeds are evidence, not final regions.** A large or statistically non-text component establishes a high-confidence starting point; it does not define the entire illustration.
3. **Weak connected support may be recovered.** Broken historical strokes may be joined when the path from a strong seed is cheap in normalized geometric cost.
4. **Ordinary text is expensive to traverse.** A nearby word or paragraph must not be absorbed merely because it touches or approaches a figure.
5. **Interior fill must be justified.** Open drawings remain open unless closing observed contour gaps is sufficiently cheap.
6. **Segmentation never whitens the source.** Paper luminance, stains and weak print inside an accepted region remain source evidence.
7. **Only the outer alpha boundary is softened.** The historical strokes themselves are not blurred as part of extraction.
8. **Page classification precedes page-scale estimation.** Cover-like, nearly blank, full-tone, or otherwise non-text-page inputs must not be forced through a text-scale model that is inapplicable.

## 3. Page observables

Let `L(x,y)` be source luminance and `B(x,y)` a slowly varying estimate of the local paper field. Define a local ink response

`I(x,y) = max(B(x,y) - L(x,y), 0)`.

A foreground-support mask is derived from `I`. Connected components are then measured by at least:

- bounding-box width `w(c)` and height `h(c)`;
- foreground area `A(c)`;
- spatial extent `e(c) = max(w(c), h(c))`;
- centroid and source-page position;
- local stroke-width evidence;
- neighborhood relations to other components.

The dominant text population is used to estimate two page-local units:

- `H_cap`: robust characteristic full-height text / capital scale;
- `W_stroke`: robust characteristic printed-stroke width.

These observables are not assumed to be globally constant across scans, resolutions, books, or rerendered fallback pages.

### 3.1 Failure-resistant text-scale estimation

The estimator must reject tiny specks and bleed-through fragments as candidate text modes. A useful architecture is:

1. classify page type from global luminance/foreground statistics;
2. find candidate component-height modes above a scale-relative dust floor;
3. score candidates by both component frequency and line-like neighborhood support;
4. estimate `H_cap` from the selected text band;
5. estimate `W_stroke` from distance-transform samples inside high-confidence text components.

This is deliberately stronger than selecting the raw mode of all component heights: degraded scans can contain more 2–4 px fragments than actual characters.

## 4. Text-likeness as a local property

A component is not text merely because it has text-like dimensions. Figure fragments can have the same size as letters.

Define a local text-likeness score `T(c) ∈ [0,1]` using evidence such as:

- similarity of `h(c)`, `w(c)` and area to the page's text population;
- nearby components with similar height;
- horizontal/baseline alignment;
- bilateral support from neighbors to the left and right;
- repeated small gaps characteristic of words or text lines.

The score is used as a **traversal penalty**, not as a destructive text-removal mask. This distinction matters where a figure and a paragraph share the same vertical band.

## 5. Strong seeds

For component `c`, a reusable normalized feature vector may contain

`f(c) = [log(h/H_cap), log(e/H_cap), log(A/(H_cap·W_stroke))]`.

Seed significance is evaluated relative to a robust model of **high-confidence text components**, not every small foreground component. This matters on pages with bleed-through: background artifacts must not broaden the reference distribution until a real illustration ceases to look exceptional.

A strong seed should combine statistical extremeness with low local text-likeness. Exceptionally extreme components may survive a moderate text-likeness score; ordinary heading/caption glyphs should not.

Border-touching scan artifacts receive a separate penalty or rejection rule when their geometry indicates page-edge noise rather than an illustration.

The seed detector should expose a per-page false-seed budget or an equivalent calibrated tail criterion rather than a hidden magic threshold.

## 6. Component graph

Create a graph `G = (V,E)` where each foreground component is a node. Edges connect components whose bounding boxes or support pixels are close enough in normalized page units.

A provisional edge cost can be decomposed as

`C(u,v) = C_gap(u,v) + λ_text·T(v) + C_artifact(v) + C_context(u,v)`.

Where:

- `C_gap` is a geometric gap measured in units of `W_stroke` and optionally `H_cap`;
- `T(v)` is local text-likeness;
- `C_artifact` penalizes tiny dust chains, page-border noise and other weak support;
- `C_context` may encode continuation/orientation evidence when validated.

The coefficients are dimensionless calibration parameters.

## 7. Multi-source geodesic growth

Run bounded multi-source shortest-path growth from all accepted seeds.

A component belongs to a candidate region only if the minimum cumulative path cost from some seed is below the calibrated growth budget. This has two desired consequences:

- a broken line can be recovered through one or more very small geometric gaps;
- entering a line of ordinary letters accumulates repeated text penalties and stops before a paragraph is consumed.

Seed ownership should be retained. Candidate regions that meet can then be treated explicitly rather than silently merged.

## 8. Candidate-region filtering

Bleed-through can produce statistically unusual but isolated components. Therefore seed existence alone is insufficient.

After growth, score each seed family / candidate region using normalized evidence such as:

- total observed foreground area;
- maximum spatial extent;
- number and strength of mutually supporting seeds;
- continuity of the grown support;
- fraction of high-text-likeness components;
- contact with suspicious page borders.

A thin rope may have low area but large extent. A compact human drawing may have high area. Region acceptance must therefore be multi-feature rather than a single area threshold.

## 9. Closure and interior fill

The original intuitive rule "mostly enclosed" is represented as a closure-cost problem.

For a grown candidate region:

1. provisionally close only gaps on a scale `k_close·W_stroke` (or another calibrated page-relative scale);
2. flood-fill from the page exterior;
3. identify newly enclosed interior;
4. measure the amount and geometry of artificial support required to create that enclosure;
5. accept the interior only when the closure cost is below the calibrated budget.

This prevents the empty space between neighboring illustrations from being filled merely because both happen to border the same background area. An open illustration remains valid; it simply receives no unjustified interior fill.

## 10. Final mask and outer margin

After accepted support and justified interior are combined, expand the region by a small page-relative outer margin, for example

`r_margin = k_margin·W_stroke`.

The purpose is to retain ambiguous weak edge pixels and local paper context without reaching into neighboring text.

A signed-distance field or equivalent boundary-distance map is then used to construct a soft alpha boundary over

`r_alpha = k_alpha·W_stroke`.

The interior remains opaque.

## 11. Archival rendering

The segmentation stage returns geometry/masks; rendering policy is caller-controlled. The intended archival use case is:

- crop the original source pixels;
- remove chroma / desaturate if desired;
- preserve source luminance inside the mask;
- apply only the outer alpha mask;
- encode the canonical derivative losslessly, typically as PNG with alpha.

No inpainting, whitening, sharpening, redrawing or smoothing of historical strokes is implied by this architecture.

## 12. Calibration model

A parameter vector `θ` contains only global **dimensionless** coefficients: seed-tail budget, text penalty, growth budget, closure scale, closure budget, margin scale, alpha width and any later validated context terms.

Optimization requires ground truth. A representative pilot should contain manual reference masks/regions and difficult negatives. One possible declared loss is

`L(θ) = λ_miss E_missed_stroke + λ_text E_text_intrusion + λ_boundary E_boundary + λ_merge E_false_merge + λ_split E_false_split + λ_fp E_false_figure`.

The weights are part of the application policy and must be published with the fitted model. Page-level bootstrap or another resampling procedure should quantify parameter/result stability before a parameter set is frozen.

## 13. Evidence and reproducibility

For each processed page the implementation should be able to emit:

- page-type decision and observables;
- `H_cap` and `W_stroke`;
- component table or a reproducible digest thereof;
- seed list and scores;
- text-likeness scores needed to audit unexpected growth;
- graph/growth parameters and model version;
- candidate-region scores;
- closure cost;
- hard and soft masks;
- bounding boxes in source coordinates;
- debug overlays;
- source SHA-256 when supplied by the caller.

The same source bytes, implementation version and frozen model parameters should produce the same segmentation outputs.