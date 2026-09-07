# App Screenshotter

`app-screenshotter` provides small reusable PySide6 primitives for capturing Qt widgets/top-level windows as PNG evidence with a machine-readable manifest.

It is deliberately **not** a universal operating-system screenshot program. The caller already owns a running Qt application and chooses what may be captured.

## Status

Experimental `0.1.0`.

## Requirements

- Python 3.11+;
- PySide6 6.8+;
- a Qt platform plugin appropriate to the environment (`xcb`, `wayland`, `windows`, `cocoa`, `offscreen`, etc.).

## Minimal integration

```python
from pathlib import Path

from app_screenshotter import capture_widget, write_manifest

record = capture_widget(
    main_window,
    output_dir=Path("artifacts/screens"),
    capture_id="main-window-dashboard",
    app=app,
)

write_manifest(
    output_dir=Path("artifacts/screens"),
    records=(record,),
    metadata={
        "commit": "abc123",
        "locale": "ru-RU",
        "theme": "Velvet",
    },
    app=app,
)
```

Capture every currently visible Qt top-level widget:

```python
from app_screenshotter import capture_visible_top_levels

manifest = capture_visible_top_levels(
    app,
    output_dir=Path("artifacts/windows"),
    metadata={"scenario": "manual-audit"},
)
```

## What is captured

Each record includes:

- capture ID and PNG filename;
- Qt widget class;
- `objectName`;
- window title;
- visibility;
- widget geometry;
- pixmap pixel and device-independent dimensions;
- device-pixel ratio;
- screen name when Qt exposes one;
- PNG size and SHA-256.

Manifest-level evidence includes Qt version, platform plugin and caller-supplied metadata.

## Capture boundary

The implementation uses `QWidget.grab()`.

That means it captures the Qt widget's rendered content, including child widgets inside the captured widget. It does **not** promise to capture operating-system window decorations, other processes, overlays rendered outside the widget, or compositor-only effects.

## Privacy boundary

This utility captures pixels exactly because that is its purpose. It performs no automatic redaction.

A screenshot can expose:

- names and free-form text;
- local paths;
- model/dataset/project identifiers;
- logs and error messages;
- tokens/secrets if the application displays them;
- user data present in the current workspace.

The caller must prepare a safe demo/audit state before producing public artifacts.

## Relationship to Persona Training Lab

The first design is extracted from the reusable capture/evidence ideas behind PTL's `tools/visual_audit.py`.

PTL's navigation registry, dependency container, LocalizationManager, workspace scenarios and release evidence rules remain PTL-specific. This snippet does not replace that harness; it supplies a smaller reusable capture boundary that another application can integrate deliberately.

See [`docs/specification.md`](docs/specification.md) and [`docs/limitations.md`](docs/limitations.md) before using captures as release evidence.
