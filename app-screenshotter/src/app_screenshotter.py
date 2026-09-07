from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping

from PySide6.QtCore import qVersion
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget


MANIFEST_SCHEMA = 1
GENERATOR = "app-screenshotter/0.1.0"
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


class ScreenshotError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class ScreenshotRecord:
    capture_id: str
    file: str
    widget_class: str
    object_name: str
    window_title: str
    visible: bool
    x: int
    y: int
    width: int
    height: int
    pixel_width: int
    pixel_height: int
    logical_width: float
    logical_height: float
    device_pixel_ratio: float
    screen_name: str | None
    bytes: int
    sha256: str


def _slug(value: str) -> str:
    normalized = _SAFE_ID.sub("-", value.strip()).strip("-._")
    if not normalized:
        raise ScreenshotError("capture id becomes empty after normalization")
    return normalized


def settle_events(app: QApplication, *, cycles: int = 3) -> None:
    for _ in range(max(0, cycles)):
        app.processEvents()


def _atomic_save_pixmap(widget: QWidget, destination: Path) -> tuple[int, str, QPixmap]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    pixmap = widget.grab()
    if pixmap.isNull():
        raise ScreenshotError(f"widget grab returned a null pixmap: {widget!r}")

    handle = tempfile.NamedTemporaryFile(
        prefix=f".{destination.name}.",
        suffix=".png",
        dir=destination.parent,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()
    try:
        if not pixmap.save(str(temp_path), "PNG"):
            raise ScreenshotError(f"Qt failed to save PNG: {destination}")
        with temp_path.open("r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        data = temp_path.read_bytes()
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return len(data), hashlib.sha256(data).hexdigest(), pixmap


def capture_widget(
    widget: QWidget,
    *,
    output_dir: Path,
    capture_id: str,
    app: QApplication | None = None,
    settle_cycles: int = 3,
) -> ScreenshotRecord:
    if app is not None:
        settle_events(app, cycles=settle_cycles)

    safe_id = _slug(capture_id)
    destination = output_dir.expanduser().resolve() / f"{safe_id}.png"
    bytes_count, sha256, pixmap = _atomic_save_pixmap(widget, destination)

    geometry = widget.geometry()
    dpr = float(pixmap.devicePixelRatio())
    logical = pixmap.deviceIndependentSize()
    screen = widget.screen()

    return ScreenshotRecord(
        capture_id=safe_id,
        file=destination.name,
        widget_class=widget.metaObject().className(),
        object_name=widget.objectName(),
        window_title=widget.windowTitle(),
        visible=widget.isVisible(),
        x=geometry.x(),
        y=geometry.y(),
        width=geometry.width(),
        height=geometry.height(),
        pixel_width=pixmap.width(),
        pixel_height=pixmap.height(),
        logical_width=round(float(logical.width()), 3),
        logical_height=round(float(logical.height()), 3),
        device_pixel_ratio=round(dpr, 4),
        screen_name=screen.name() if screen is not None else None,
        bytes=bytes_count,
        sha256=sha256,
    )


def _window_sort_key(widget: QWidget) -> tuple[object, ...]:
    geometry = widget.geometry()
    return (
        widget.metaObject().className(),
        widget.objectName(),
        widget.windowTitle(),
        geometry.x(),
        geometry.y(),
        geometry.width(),
        geometry.height(),
    )


def _window_capture_id(index: int, widget: QWidget) -> str:
    identity = widget.objectName() or widget.windowTitle() or widget.metaObject().className()
    return _slug(f"{index:03d}-{widget.metaObject().className()}-{identity}")


def write_manifest(
    *,
    output_dir: Path,
    records: tuple[ScreenshotRecord, ...],
    metadata: Mapping[str, str] | None = None,
    app: QApplication | None = None,
) -> dict[str, object]:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "generator": GENERATOR,
        "qt_version": qVersion(),
        "platform_plugin": app.platformName() if app is not None else None,
        "metadata": dict(sorted((metadata or {}).items())),
        "captures": [asdict(record) for record in records],
    }
    data = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    destination = output_dir / "manifest.json"
    handle = tempfile.NamedTemporaryFile(
        prefix=".manifest.",
        suffix=".tmp",
        dir=output_dir,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()
    try:
        temp_path.write_bytes(data)
        with temp_path.open("r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return payload


def capture_visible_top_levels(
    app: QApplication,
    *,
    output_dir: Path,
    metadata: Mapping[str, str] | None = None,
    settle_cycles: int = 3,
) -> dict[str, object]:
    settle_events(app, cycles=settle_cycles)
    widgets = tuple(
        sorted(
            (widget for widget in app.topLevelWidgets() if widget.isVisible()),
            key=_window_sort_key,
        )
    )

    records = tuple(
        capture_widget(
            widget,
            output_dir=output_dir,
            capture_id=_window_capture_id(index, widget),
            app=None,
        )
        for index, widget in enumerate(widgets, start=1)
    )
    return write_manifest(
        output_dir=output_dir,
        records=records,
        metadata=metadata,
        app=app,
    )
