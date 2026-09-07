from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import app_screenshotter as screenshotter  # noqa: E402


class ScreenshotterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_capture_widget_writes_png_and_hash_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            widget = QLabel("Visible evidence")
            widget.setObjectName("evidenceLabel")
            widget.resize(240, 80)
            widget.show()
            try:
                record = screenshotter.capture_widget(
                    widget,
                    output_dir=output,
                    capture_id="label evidence",
                    app=self.app,
                )
                data = (output / record.file).read_bytes()
            finally:
                widget.close()

            self.assertEqual(record.capture_id, "label-evidence")
            self.assertGreater(record.bytes, 0)
            self.assertEqual(record.sha256, hashlib.sha256(data).hexdigest())
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")

    def test_visible_top_levels_write_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            window = QWidget()
            window.setObjectName("mainWindow")
            window.setWindowTitle("Main")
            window.resize(320, 160)
            window.show()
            try:
                payload = screenshotter.capture_visible_top_levels(
                    self.app,
                    output_dir=output,
                    metadata={"scenario": "test"},
                )
            finally:
                window.close()

            persisted = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload, persisted)
            self.assertEqual(persisted["schema"], 1)
            self.assertEqual(persisted["metadata"], {"scenario": "test"})
            self.assertTrue(
                any(item["object_name"] == "mainWindow" for item in persisted["captures"])
            )

    def test_empty_capture_id_is_rejected(self) -> None:
        widget = QWidget()
        try:
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(screenshotter.ScreenshotError):
                    screenshotter.capture_widget(
                        widget,
                        output_dir=Path(temp),
                        capture_id="***",
                    )
        finally:
            widget.close()


if __name__ == "__main__":
    unittest.main()
