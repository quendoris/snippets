# Limitations

## PySide6 only

v0.1 is a Qt/PySide6 in-process capture utility.

It does not capture arbitrary native windows from other applications and is not a replacement for platform screenshot APIs.

## `QWidget.grab()` boundary

The PNG reflects Qt's captured widget content. It does not guarantee inclusion of:

- operating-system title bars/borders;
- compositor shadows;
- external overlays;
- menus/tooltips implemented as other top-level windows unless those are captured separately;
- GPU/compositor effects that are not represented in the grabbed widget surface.

## Event settling is bounded and synchronous

Several `processEvents()` calls do not prove that asynchronous work, network I/O, training, timers, animations, worker threads, or queued background projections have reached a stable semantic state.

Applications must define their own scenario-ready condition before calling the snippet when content stability matters.

## Screenshots are not deterministic bytes

Unlike `archive-bundler`, this snippet does not claim byte-identical PNG output across platforms/runs.

Rendering can vary with:

- Qt version;
- platform plugin;
- operating system;
- font availability/rasterization;
- DPI/device-pixel ratio;
- GPU/compositor behavior;
- theme/style state;
- animation/cursor/timing;
- application data.

The manifest records some of these inputs, not all of them.

## No automatic redaction

The snippet performs no secret/PII/path redaction and cannot decide whether visible application data is safe to publish.

Treat captures as potentially sensitive until reviewed.

## Window enumeration can be semantically ambiguous

Sorting visible top levels by class/name/title/geometry improves stability but does not create a persistent identity for otherwise identical windows.

For reproducible named evidence, the host application should capture known widgets explicitly with caller-assigned IDs.

## No annotations/cropping

v0.1 captures the whole selected widget. It does not add arrows, labels, masks, crops, highlights, or comparison overlays.

Those transformations should remain separate from raw evidence capture so the original PNG/hash can be preserved.

## No archive output

The snippet intentionally stops at PNG + JSON manifest. Use `archive-bundler` or another artifact layer when a single archive is required.

## No directory-level transaction

Each PNG and the final manifest are published atomically as individual files, but the entire capture set is not one atomic filesystem transaction.

An interruption after several screenshots but before manifest publication can leave partial PNGs in the output directory.

Use a fresh scenario output directory for strict evidence workflows, or wrap directory publication at a higher layer.

## No overwrite policy switch

Named captures replace an existing PNG with the same normalized capture ID. The snippet currently has no `fail-if-exists` mode.

## Manifest does not hash itself

The manifest records hashes for PNGs, not a self-hash/signature. Authenticity and tamper-evident signing belong to a higher-level evidence system.
