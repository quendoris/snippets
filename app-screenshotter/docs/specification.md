# Specification

## Public functions

### `settle_events(app, cycles=3)`

Calls `app.processEvents()` `max(0, cycles)` times.

No sleep, timer wait, worker join or application-specific readiness condition is implied.

### `capture_widget(...) -> ScreenshotRecord`

Required:

- `widget: QWidget`
- `output_dir: Path`
- `capture_id: str`

Optional:

- `app: QApplication | None`
- `settle_cycles: int = 3`

When `app` is supplied, event settling occurs before `QWidget.grab()`.

`capture_id` is normalized to characters in:

```text
A-Z a-z 0-9 . _ -
```

Runs of other characters become `-`; leading/trailing punctuation is removed. An empty normalized ID is rejected.

The destination is:

```text
<output_dir>/<normalized-capture-id>.png
```

### `write_manifest(...) -> dict`

Writes:

```text
<output_dir>/manifest.json
```

The manifest is generated from supplied `ScreenshotRecord` objects and caller metadata.

### `capture_visible_top_levels(...) -> dict`

Captures every currently visible object in `app.topLevelWidgets()` after event settling, then writes one manifest.

## `ScreenshotRecord`

Current fields:

```text
capture_id
file
widget_class
object_name
window_title
visible
x
y
width
height
pixel_width
pixel_height
logical_width
logical_height
device_pixel_ratio
screen_name
bytes
sha256
```

Geometry values come from `QWidget.geometry()` at capture time.

`pixel_width`/`pixel_height` come from `QPixmap.width()`/`height()`.

Logical dimensions come from `QPixmap.deviceIndependentSize()` and are rounded to three decimal places.

Device-pixel ratio is rounded to four decimal places.

## Manifest schema

Current schema value:

```text
1
```

Shape:

```json
{
  "schema": 1,
  "generator": "app-screenshotter/0.1.0",
  "qt_version": "...",
  "platform_plugin": "offscreen",
  "metadata": {},
  "captures": []
}
```

Caller metadata values are strings and keys are sorted during serialization.

The manifest is written as UTF-8 JSON with sorted object keys and an ending newline.

## PNG write semantics

For each capture:

1. call `widget.grab()`;
2. reject a null pixmap;
3. create a temporary `.png` file in the destination directory;
4. save using Qt's explicit `PNG` format;
5. fsync the temporary file;
6. read exact PNG bytes and calculate SHA-256;
7. publish with `os.replace()`.

If Qt reports image-save failure, `ScreenshotError` is raised and the destination is not replaced by that temporary file.

## Top-level ordering

Visible top-level widgets are sorted by:

```text
widget class
objectName
windowTitle
geometry x/y/width/height
```

Generated IDs include a one-based three-digit index plus class and best available identity (`objectName`, then title, then class).

## Threading requirement

Qt widget operations are expected to be invoked from the GUI thread according to Qt application rules.

The snippet does not marshal calls between threads.

## Side effects

The snippet:

- processes pending Qt events when requested;
- reads widget state/pixels;
- creates/replaces PNG files below the requested output directory;
- creates/replaces `manifest.json`.

It does not navigate the application, modify domain/workspace data, archive outputs, or upload captures.
