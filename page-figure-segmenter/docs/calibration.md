# Calibration model

This document formalizes how the eventual reusable parameter set should be fitted. It is intentionally independent of any one book.

## 1. What is measured per page

For page `p`, derive page-local observables rather than fixed pixel constants:

- `H_cap(p)` — robust full-height text scale;
- `W_stroke(p)` — robust printed-stroke scale;
- page luminance/background statistics;
- component feature distributions;
- local text-likeness scores.

All ordinary geometric hyperparameters are dimensionless multipliers of these observables.

## 2. Global parameter vector

A provisional parameter vector may contain

`θ = (α_seed, λ_text, τ_growth, k_edge, k_join, τ_region, k_close, τ_close, k_margin, k_alpha, ...)`

where, conceptually:

- `α_seed` controls the per-page false-seed tail budget;
- `λ_text` is the geodesic penalty for traversing text-like support;
- `τ_growth` is the maximum cumulative path cost;
- `k_edge` controls maximum graph-edge distance in `W_stroke`/`H_cap` units;
- `k_join` controls when seed families may be coalesced;
- `τ_region` denotes candidate-region acceptance thresholds or model parameters;
- `k_close` is the provisional closure radius in stroke units;
- `τ_close` is the maximum accepted closure cost;
- `k_margin` is the archival outer-margin width in stroke units;
- `k_alpha` is the alpha-feather width in stroke units.

The exact vector is allowed to change while the project-local implementation is being measured. A parameter is not frozen merely because it produced a visually good pilot result.

## 3. Reference data

Calibration requires source-page images plus human reference annotations. At minimum annotate:

- whether the page is in the calibrated text-page domain;
- number of intended figure assets;
- source-coordinate region/mask for each figure;
- intentional grouping of visually disjoint pieces that form one archival figure;
- cases where a long line is part of a figure versus a typographic rule;
- ambiguous weak strokes where preservation is preferable to clipping.

OCR or caption text may help stratify/select pages, but the reference annotation remains external evaluation data and must not leak into image-to-mask inference.

## 4. Split before fitting

Create at least three roles:

- **development** pages for implementation/debugging;
- **calibration** pages used to fit `θ`;
- **held-out validation** pages never used to choose parameters.

When the dataset is small, repeated grouped cross-validation may supplement a fixed holdout, but a final untouched set should remain for the pre-release claim.

Split at the page/source-document level so near-duplicate crops from one physical illustration do not appear on both sides of the evaluation.

## 5. Loss

For a reference figure `R` and predicted figure `P`, keep failure classes separate rather than hiding them inside one IoU number.

A candidate objective is

`L(θ) = λ_miss E_miss + λ_text E_text + λ_boundary E_boundary + λ_merge E_merge + λ_split E_split + λ_fp E_false_figure + λ_domain E_domain`.

Interpretation:

- `E_miss` — true figure support/strokes omitted;
- `E_text` — ordinary text or unrelated page matter included;
- `E_boundary` — geometric boundary disagreement after accounting for the intended archival margin;
- `E_merge` — two intended assets merged;
- `E_split` — one intended asset fragmented into multiple outputs;
- `E_false_figure` — accepted figure on a negative page;
- `E_domain` — page-type/domain classification error.

For archival extraction, missed weak strokes and text intrusion both deserve high cost. Their relative weight is an explicit application policy, not an implementation accident.

## 6. Metrics reported separately

Always report at least:

- page-domain classification confusion matrix;
- negative-page false-figure rate;
- positive-page figure recall;
- figure-count exact-match rate;
- false-merge rate;
- false-split rate;
- pixel/stroke recall on annotated masks;
- text-intrusion area/rate;
- boundary error;
- closure false-fill rate;
- per-failure-class examples.

Aggregate scores are useful only after these components remain visible.

## 7. Closure cost

Do not define closure as a literal percentage of an enclosing contour. Let `M` be observed grown support, `C_k(M)` a provisional close at scale `k_close`, and `A_bridge = C_k(M) \ M` the artificial support introduced by closing.

A closure-cost family may include terms such as

`J_close = |A_bridge| / (P(M) · r_close) + β_span·G_span + β_topology·G_topology`

where `P(M)` is observed contour length and `r_close` is the close radius. The first normalization avoids treating ordinary morphological thickening as if it were proportional to total figure area. Gap-span/topology terms may later distinguish many tiny repairs from one implausibly large bridge.

The exact formula must be selected against annotated open/closed drawings, not frozen from one pilot page.

## 8. Region grouping

Grouping is evaluated independently from pixel segmentation. Two disjoint support regions may belong to one archival figure when their layout forms one composed illustration.

Candidate grouping evidence may include:

- rectangle overlap/nesting;
- small vertical gap plus strong horizontal overlap;
- small horizontal gap plus strong vertical overlap;
- low-cost support continuity;
- compatible scale and orientation.

Caption identity may be used only as evaluation truth in a non-semantic image-only mode.

## 9. Optimization

Because some parameters are discontinuous thresholds, do not assume a gradient method is appropriate. Viable approaches include:

- coarse-to-fine grid search for the first low-dimensional model;
- Bayesian optimization once evaluation is deterministic and moderately expensive;
- mixed discrete/continuous search if region rules remain categorical.

Every trial should write its complete `θ`, dataset version and metric vector so the chosen point is reproducible.

## 10. Uncertainty and stability

After selecting a candidate `θ*`, resample at the page level and refit/re-evaluate. Record:

- bootstrap confidence intervals for major metrics;
- distribution of each fitted parameter when refitting is feasible;
- sensitivity curves around `θ*`;
- pages whose classification changes under small parameter perturbations.

A useful parameter set should occupy a reasonably stable basin. A razor-thin optimum that collapses after a tiny coefficient change is not ready to be called robust.

## 11. Freeze rule

A parameter set receives a version only when:

1. its calibration data and annotations are versioned;
2. its exact parameter vector is recorded;
3. held-out metrics pass the declared acceptance gates;
4. known failures are documented;
5. the project-local full-corpus dry run has been sampled manually;
6. the reusable implementation reproduces the project-local reference results.

Until then, numerical values remain research parameters, even if they look excellent in a visual preview.