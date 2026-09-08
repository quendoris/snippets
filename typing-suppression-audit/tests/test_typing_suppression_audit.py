from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "typing_suppression_audit.py"
)
SPEC = importlib.util.spec_from_file_location("typing_suppression_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TypingSuppressionAuditTests(unittest.TestCase):
    def test_source_scanner_uses_comment_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "sample.py"
            source.parent.mkdir(parents=True)
            source.write_text(
                'example = "# type: ignore"\n'
                "value = call()  # type: ignore[arg-type]\n",
                encoding="utf-8",
            )

            findings = MODULE.scan(
                root=root,
                code_roots=(Path("src"),),
                config_paths=(),
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].kind, "type_ignore")
            self.assertEqual(findings[0].line, 2)

    def test_default_policy_blocks_every_finding(self) -> None:
        finding = MODULE.Finding(
            path="tests/test_sample.py",
            line=4,
            kind="type_ignore",
            text="# type: ignore[arg-type]",
        )
        classified = MODULE.classify((finding,))
        self.assertEqual(len(classified), 1)
        self.assertTrue(classified[0].blocking)

    def test_explicit_test_prefix_can_downgrade_only_coded_ignore(self) -> None:
        coded = MODULE.Finding(
            path="tests/test_sample.py",
            line=4,
            kind="type_ignore",
            text="# type: ignore[arg-type]",
        )
        broad = MODULE.Finding(
            path="tests/test_sample.py",
            line=5,
            kind="type_ignore",
            text="# type: ignore",
        )
        classified = MODULE.classify(
            (coded, broad),
            informational_coded_ignore_prefixes=("tests/",),
        )
        self.assertFalse(classified[0].blocking)
        self.assertTrue(classified[1].blocking)

    def test_config_suppressions_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "mypy.ini"
            config.write_text(
                "[mypy-package.*]\nignore_errors = true\n",
                encoding="utf-8",
            )
            findings = MODULE.scan(
                root=root,
                code_roots=(),
                config_paths=(Path("mypy.ini"),),
            )
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].kind, "mypy_ignore_errors_config")

    def test_payload_counts_blocking_and_informational(self) -> None:
        findings = (
            MODULE.ClassifiedFinding(
                MODULE.Finding("src/a.py", 1, "type_ignore", "# type: ignore"),
                True,
            ),
            MODULE.ClassifiedFinding(
                MODULE.Finding(
                    "tests/a.py", 2, "type_ignore", "# type: ignore[arg-type]"
                ),
                False,
            ),
        )
        report = MODULE.payload(findings)
        self.assertFalse(report["passed"])
        self.assertEqual(report["finding_count"], 2)
        self.assertEqual(report["blocking_finding_count"], 1)
        self.assertEqual(report["informational_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
