import hashlib
import importlib.util
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "page_evidence_batcher", HERE / "src" / "page_evidence_batcher.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class PageEvidenceBatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pages").mkdir()
        (self.root / "ocr" / "a").mkdir(parents=True)
        self.records = []
        for idx in (10, 11):
            page_id = f"p{idx}"
            page = self.root / "pages" / f"{page_id}.jpg"
            page.write_bytes(f"page-{idx}".encode())
            evidence = self.root / "ocr" / "a" / f"{page_id}.txt"
            evidence.write_text(f"evidence-{idx}\n", encoding="utf-8")
            self.records.append(
                {
                    "id": page_id,
                    "physical_index": idx,
                    "path": str(page.relative_to(self.root)),
                    "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                    "side": "left" if idx == 10 else "right",
                }
            )
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"records": self.records}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_batch(self):
        _, records = mod.load_manifest(self.manifest, "records")
        specs = mod.parse_evidence_specs(["ocr=ocr/a/{id}.txt"])
        planned = mod.plan_batch(
            records=records,
            start=10,
            count=2,
            id_field="id",
            index_field="physical_index",
            source_field="path",
            sha256_field="sha256",
            source_base=self.root,
            evidence_base=self.root,
            evidence_specs=specs,
        )
        return mod.publish_batch(
            out_dir=self.root / "out",
            name_prefix="review",
            planned=planned,
            source_manifest=self.manifest,
            evidence_specs=specs,
            carry_fields=["side"],
        )

    def test_happy_path_and_manifest(self):
        directory, archive, manifest = self.run_batch()
        self.assertTrue(directory.is_dir())
        self.assertTrue(archive.is_file())
        self.assertEqual(manifest["range"], {"start": 10, "end": 11, "count": 2})
        self.assertEqual(manifest["records"][0]["metadata"]["side"], "left")
        self.assertEqual(
            (directory / manifest["records"][1]["evidence"]["ocr"]).read_text(),
            "evidence-11\n",
        )

    def test_archive_is_deterministic(self):
        _, archive, _ = self.run_batch()
        first = archive.read_bytes()
        _, archive, _ = self.run_batch()
        self.assertEqual(first, archive.read_bytes())
        with tarfile.open(archive, "r:gz") as tf:
            names = tf.getnames()
        self.assertIn("review-0010-0011/manifest.json", names)

    def test_hash_mismatch_fails_before_publication(self):
        broken = json.loads(self.manifest.read_text())
        broken["records"][0]["sha256"] = "0" * 64
        self.manifest.write_text(json.dumps(broken))
        _, records = mod.load_manifest(self.manifest, "records")
        specs = mod.parse_evidence_specs(["ocr=ocr/a/{id}.txt"])
        with self.assertRaises(mod.BatchError):
            mod.plan_batch(
                records=records,
                start=10,
                count=2,
                id_field="id",
                index_field="physical_index",
                source_field="path",
                sha256_field="sha256",
                source_base=self.root,
                evidence_base=self.root,
                evidence_specs=specs,
            )
        self.assertFalse((self.root / "out").exists())

    def test_missing_evidence_is_rejected(self):
        (self.root / "ocr" / "a" / "p11.txt").unlink()
        _, records = mod.load_manifest(self.manifest, "records")
        specs = mod.parse_evidence_specs(["ocr=ocr/a/{id}.txt"])
        with self.assertRaises(mod.BatchError):
            mod.plan_batch(
                records=records,
                start=10,
                count=2,
                id_field="id",
                index_field="physical_index",
                source_field="path",
                sha256_field="sha256",
                source_base=self.root,
                evidence_base=self.root,
                evidence_specs=specs,
            )

    def test_unsafe_id_is_rejected(self):
        bad = [dict(self.records[0], id="../escape")]
        with self.assertRaises(mod.BatchError):
            mod.plan_batch(
                records=bad,
                start=10,
                count=1,
                id_field="id",
                index_field="physical_index",
                source_field="path",
                sha256_field="sha256",
                source_base=self.root,
                evidence_base=self.root,
                evidence_specs=[],
            )


if __name__ == "__main__":
    unittest.main()
