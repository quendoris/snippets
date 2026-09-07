from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import codebase_anatomy as anatomy  # noqa: E402


class PythonCountingTests(unittest.TestCase):
    def test_python_code_count_excludes_comments_and_docstrings(self) -> None:
        source = '''"""module doc"""

# comment
VALUE = 1


def f() -> int:
    """function doc"""
    # another comment
    return VALUE
'''
        self.assertEqual(anatomy._python_code_lines(source), 3)


class LanguageAndRoleTests(unittest.TestCase):
    def test_language_detection_is_extension_based(self) -> None:
        self.assertEqual(anatomy._language(Path("main.rs")), "Rust")
        self.assertEqual(anatomy._language(Path("guide.md")), "Markdown")
        self.assertEqual(anatomy._language(Path("Dockerfile")), "Dockerfile")

    def test_tests_are_structural_role_before_production_code(self) -> None:
        self.assertEqual(anatomy._role("tests/test_widget.py", "Python"), "tests")
        self.assertEqual(anatomy._role("src/widget.py", "Python"), "production-code")


class SemanticGroupTests(unittest.TestCase):
    def test_groups_may_overlap_and_exclusions_win(self) -> None:
        groups = (
            anatomy.SemanticGroup("core", ("src/**",)),
            anatomy.SemanticGroup("critical", ("src/**",), ("src/generated/**",)),
        )
        self.assertEqual(
            anatomy._semantic_groups("src/domain/model.py", groups),
            ("core", "critical"),
        )
        self.assertEqual(
            anatomy._semantic_groups("src/generated/schema.py", groups),
            ("core",),
        )

    def test_config_loads_project_declared_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "codebase-anatomy.toml"
            path.write_text(
                '''[settings]
ignore = ["vendor/**"]

[[group]]
name = "architecture"
include = ["src/**/architecture/**"]

[[group]]
name = "critical-tests"
include = ["tests/test_*_safety.py"]
''',
                encoding="utf-8",
            )
            ignores, groups = anatomy._load_config(path)

        self.assertIn("vendor/**", ignores)
        self.assertEqual(tuple(group.name for group in groups), ("architecture", "critical-tests"))


class ApproximateCountingTests(unittest.TestCase):
    def test_c_style_estimate_drops_comment_only_lines(self) -> None:
        source = '''// comment
int x = 1;
/* block
comment */
int y = 2; // trailing
'''
        self.assertEqual(anatomy._approximate_code_lines(source, "C"), 2)


if __name__ == "__main__":
    unittest.main()
