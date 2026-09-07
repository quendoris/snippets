# Architecture

## Scope

`app-screenshotter` intentionally begins **inside** a running PySide6 process.

It does not discover or attach to arbitrary external OS windows. That keeps the reusable boundary small and predictable:

```text
caller-owned QApplication/QWidget
        ↓
optional event settling
        ↓
QWidget.grab()
        ↓
PNG temporary file
        ↓
fsync + os.replace()
        ↓
ScreenshotRecord
        ↓
manifest.json
```

## Explicit caller ownership

The host application owns:

- application startup/shutdown;
- navigation/scenario preparation;
- demo/workspace data;
- theme, locale and scale selection;
- whether a particular widget is safe to capture;
- any redaction required before capture.

The snippet owns only image/evidence production after a widget has been selected.

## Event settling

`settle_events()` runs `QApplication.processEvents()` for a bounded number of cycles.

`capture_widget()` can request that settling before capture when the caller supplies the `QApplication` object.

This is a pragmatic Qt rendering aid, not proof that asynchronous application work has completed. Applications with background workers must expose their own scenario-ready condition.

## PNG publication

The widget is captured through `QWidget.grab()` to a `QPixmap`.

The PNG is first written to a temporary file in the destination directory. The file is fsynced and then published through `os.replace()`.

This avoids leaving a partially written destination PNG when Qt image saving fails part-way through normal operation.

## Evidence record

`ScreenshotRecord` keeps image identity separate from caller metadata.

Per-capture fields describe what Qt directly exposed at capture time plus byte evidence for the resulting PNG.

The PNG hash is SHA-256 of the exact published file bytes.

## Top-level collection

`capture_visible_top_levels()`:

1. settles events;
2. selects visible `QApplication.topLevelWidgets()`;
3. sorts them by a stable tuple of class/object/title/geometry values;
4. derives numbered capture IDs;
5. captures each widget;
6. writes one manifest for the resulting record set.

Sorting reduces incidental ordering differences from Qt's top-level-widget enumeration. Identical windows can still be ambiguous; strict audit scenarios should capture known widgets explicitly by caller-defined IDs.

## Manifest

`manifest.json` contains:

- schema version;
- generator identity;
- Qt version;
- Qt platform plugin when an application instance is supplied;
- sorted caller metadata;
- ordered capture records.

No implicit wall-clock timestamp is added. If time is part of the evidence contract, the caller must provide it as metadata deliberately.

## Separation from archive creation

This snippet does not ZIP its outputs.

That is intentional separation of responsibility. A caller can feed the resulting PNG directory/manifest to `archive-bundler` or another artifact system after reviewing whether the capture set is safe and complete.
