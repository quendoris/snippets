from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import archive_bundler as bundler  # noqa: E402


class BundleTests(unittest.TestCase):
    def test_same_inputs_produce_identical_archive_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "source"
            base.mkdir()
            (base / "a.txt").write_text("alpha\n", encoding="utf-8")
            nested = base / "nested"
            nested.mkdir()
            (nested / "b.json").write_text('{"b": 2}\n', encoding="utf-8")

            first = root / "first.zip"
            second = root / "second.zip"
            metadata = {"commit": "abc123", "purpose": "test"}

            bundler.build_bundle(
                base=base,
                sources=(Path("."),),
                output=first,
                metadata=metadata,
            )
            bundler.build_bundle(
                base=base,
                sources=(Path("."),),
                output=second,
                metadata=metadata,
            )

            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_manifest_records_source_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "source"
            base.mkdir()
            data = b"payload\n"
            (base / "artifact.bin.txt").write_bytes(data)
            output = root / "bundle.zip"

            bundler.build_bundle(
                base=base,
                sources=(Path("artifact.bin.txt"),),
                output=output,
            )

            with zipfile.ZipFile(output) as archive:
                manifest = json.loads(
                    archive.read("_bundle/manifest.json").decode("utf-8")
                )
                names = archive.namelist()

            self.assertEqual(
                names,
                [
                    "_bundle/manifest.json",
                    "_bundle/summary.md",
                    "artifact.bin.txt",
                ],
            )
            self.assertEqual(manifest["schema"], 1)
            self.assertEqual(manifest["totals"], {"bytes": len(data), "files": 1})
            self.assertEqual(manifest["files"][0]["path"], "artifact.bin.txt")
            self.assertEqual(
                manifest["files"][0]["sha256"],
                hashlib.sha256(data).hexdigest(),
            )

    def test_source_outside_base_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            base.mkdir()
            outside = root / "outside.txt"
            outside.write_text("nope", encoding="utf-8")

            with self.assertRaises(bundler.BundleError):
                bundler.build_bundle(
                    base=base,
                    sources=(outside,),
                    output=root / "bundle.zip",
                )

    def test_reserved_bundle_namespace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "base"
            reserved = base / "_bundle"
            reserved.mkdir(parents=True)
            (reserved / "user.txt").write_text("ambiguous", encoding="utf-8")

            with self.assertRaises(bundler.BundleError):
                bundler.build_bundle(
                    base=base,
                    sources=(Path("_bundle"),),
                    output=root / "bundle.zip",
                )

    def test_duplicate_metadata_keys_are_rejected(self) -> None:
        with self.assertRaises(bundler.BundleError):
            bundler._parse_metadata(["commit=abc", "commit=def"])


if __name__ == "__main__":
    unittest.main()
