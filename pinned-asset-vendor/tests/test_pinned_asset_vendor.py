from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import pinned_asset_vendor as vendor  # noqa: E402


class ManifestTests(unittest.TestCase):
    def test_loads_exact_asset_identity(self) -> None:
        data = b"asset-bytes"
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = Path(temporary) / "assets.toml"
            manifest_path.write_text(
                f'''schema = 1
user_agent = "fixture/1"

[[asset]]
name = "fixture"
source_url = "https://example.invalid/commit/asset.bin"
destination = "vendor/asset.bin"
size = {len(data)}
sha256 = "{hashlib.sha256(data).hexdigest()}"
git_blob_sha1 = "{vendor.git_blob_sha1(data)}"
''',
                encoding="utf-8",
            )
            manifest = vendor.load_manifest(manifest_path)

        self.assertEqual(manifest.user_agent, "fixture/1")
        self.assertEqual(len(manifest.assets), 1)
        self.assertEqual(manifest.assets[0].destination, "vendor/asset.bin")

    def test_rejects_parent_traversal_and_http(self) -> None:
        data = b"x"
        sha = hashlib.sha256(data).hexdigest()
        cases = (
            ("https://example.invalid/a", "../escape.bin"),
            ("http://example.invalid/a", "vendor/a.bin"),
        )
        for url, destination in cases:
            with self.subTest(url=url, destination=destination):
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "assets.toml"
                    path.write_text(
                        f'''schema = 1
[[asset]]
name = "bad"
source_url = "{url}"
destination = "{destination}"
size = 1
sha256 = "{sha}"
''',
                        encoding="utf-8",
                    )
                    with self.assertRaises(vendor.VendorConfigurationError):
                        vendor.load_manifest(path)


class IntegrityTests(unittest.TestCase):
    def test_size_and_sha256_are_both_required(self) -> None:
        data = b"right"
        spec = vendor.AssetSpec(
            name="fixture",
            source_url="https://example.invalid/a",
            destination="a.bin",
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )
        result = vendor.verify_bytes(data, spec)
        self.assertEqual(result.sha256, hashlib.sha256(data).hexdigest())

        with self.assertRaises(vendor.AssetIntegrityError):
            vendor.verify_bytes(data + b"!", spec)

        wrong_hash = vendor.AssetSpec(
            name="fixture",
            source_url=spec.source_url,
            destination=spec.destination,
            size=len(data),
            sha256="0" * 64,
        )
        with self.assertRaises(vendor.AssetIntegrityError):
            vendor.verify_bytes(data, wrong_hash)

    def test_git_blob_identity_is_checked_when_declared(self) -> None:
        data = b"git-backed"
        spec = vendor.AssetSpec(
            name="fixture",
            source_url="https://example.invalid/a",
            destination="a.bin",
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            git_blob_sha1="0" * 40,
        )
        with self.assertRaises(vendor.AssetIntegrityError):
            vendor.verify_bytes(data, spec)


class VendoringTests(unittest.TestCase):
    def _spec(self, data: bytes) -> vendor.AssetSpec:
        return vendor.AssetSpec(
            name="fixture",
            source_url="https://example.invalid/exact/asset.bin",
            destination="vendor/asset.bin",
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            git_blob_sha1=vendor.git_blob_sha1(data),
        )

    def test_vendor_publishes_verified_download_atomically(self) -> None:
        data = b"verified-content"
        spec = self._spec(data)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(vendor, "_download", return_value=data) as download:
                result = vendor.vendor_asset(
                    root,
                    spec,
                    user_agent="test/1",
                    timeout=1.0,
                )
            self.assertEqual(result.action, "vendored")
            self.assertEqual((root / spec.destination).read_bytes(), data)
            download.assert_called_once()
            self.assertFalse(any((root / "vendor").glob("*.tmp")))

    def test_existing_verified_asset_avoids_network(self) -> None:
        data = b"already-correct"
        spec = self._spec(data)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / spec.destination
            destination.parent.mkdir(parents=True)
            destination.write_bytes(data)
            with patch.object(vendor, "_download") as download:
                result = vendor.vendor_asset(
                    root,
                    spec,
                    user_agent="test/1",
                    timeout=1.0,
                )
            self.assertEqual(result.action, "already-verified")
            download.assert_not_called()

    def test_check_mode_never_calls_network(self) -> None:
        data = b"offline"
        spec = self._spec(data)
        manifest = vendor.VendorManifest("test/1", (spec,))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / spec.destination
            destination.parent.mkdir(parents=True)
            destination.write_bytes(data)
            with patch.object(vendor, "_download") as download:
                results = vendor.run(
                    root=root,
                    manifest=manifest,
                    check_only=True,
                    timeout=1.0,
                )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].action, "verified")
            download.assert_not_called()

    def test_bad_download_does_not_replace_existing_destination(self) -> None:
        expected = b"expected"
        existing = b"old-invalid"
        spec = self._spec(expected)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / spec.destination
            destination.parent.mkdir(parents=True)
            destination.write_bytes(existing)
            with patch.object(vendor, "_download", return_value=b"wrong"):
                with self.assertRaises(vendor.AssetIntegrityError):
                    vendor.vendor_asset(
                        root,
                        spec,
                        user_agent="test/1",
                        timeout=1.0,
                    )
            self.assertEqual(destination.read_bytes(), existing)


if __name__ == "__main__":
    unittest.main()
