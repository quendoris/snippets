from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import release_gate_runner as gate  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_loads_manifest_and_preserves_exact_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "release-gate.toml"
            config.write_text(
                '''[gate]
name = "Example"
require_clean_worktree = false
output = "evidence"

[[step]]
name = "check"
command = ["{python}", "-c", "print('hello world')"]
blocking = false
repeat = 2
''',
                encoding="utf-8",
            )
            loaded = gate.load_config(config)

        self.assertEqual(loaded.name, "Example")
        self.assertFalse(loaded.require_clean_worktree)
        self.assertEqual(loaded.output, Path("evidence"))
        self.assertEqual(len(loaded.steps), 1)
        self.assertEqual(loaded.steps[0].command[1:], ("-c", "print('hello world')"))
        self.assertFalse(loaded.steps[0].blocking)
        self.assertEqual(loaded.steps[0].repeat, 2)

    def test_rejects_duplicate_step_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "gate.toml"
            config.write_text(
                '''[gate]
require_clean_worktree = false

[[step]]
name = "same"
command = ["one"]

[[step]]
name = "same"
command = ["two"]
''',
                encoding="utf-8",
            )
            with self.assertRaises(gate.GateConfigurationError):
                gate.load_config(config)


class RunnerTests(unittest.TestCase):
    def _config(self, steps: tuple[gate.GateStep, ...]) -> gate.GateConfig:
        return gate.GateConfig(
            name="Test gate",
            require_clean_worktree=False,
            output=Path("evidence"),
            environment=(),
            steps=steps,
        )

    def test_nonblocking_failure_continues_and_writes_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "gate.toml"
            config_path.write_text("# test fixture\n", encoding="utf-8")
            steps = (
                gate.GateStep(
                    "warning",
                    ("{python}", "-c", "import sys; sys.exit(3)"),
                    False,
                    1,
                    (),
                ),
                gate.GateStep(
                    "pass",
                    ("{python}", "-c", "print('ok')"),
                    True,
                    2,
                    (),
                ),
            )
            runner = gate.ReleaseGateRunner(
                root=root,
                config_path=config_path,
                config=self._config(steps),
                seed=123,
            )
            result = runner.run()
            summary = json.loads(
                (runner.output_dir / "summary.json").read_text(encoding="utf-8")
            )

            self.assertEqual(result, 0)
            self.assertTrue(summary["passed"])
            self.assertEqual(summary["warnings"], ["warning"])
            self.assertEqual(
                [item["name"] for item in summary["results"]],
                ["warning", "pass-01", "pass-02"],
            )
            self.assertTrue((runner.output_dir / "warning.log").is_file())
            self.assertTrue((runner.output_dir / "pass-02.log").is_file())
            self.assertTrue((runner.output_dir / "summary.md").is_file())

    def test_blocking_failure_stops_later_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "should-not-exist.txt"
            config_path = root / "gate.toml"
            config_path.write_text("# test fixture\n", encoding="utf-8")
            steps = (
                gate.GateStep(
                    "fail",
                    ("{python}", "-c", "import sys; sys.exit(9)"),
                    True,
                    1,
                    (),
                ),
                gate.GateStep(
                    "later",
                    (
                        "{python}",
                        "-c",
                        "from pathlib import Path; Path('should-not-exist.txt').write_text('x')",
                    ),
                    True,
                    1,
                    (),
                ),
            )
            runner = gate.ReleaseGateRunner(
                root=root,
                config_path=config_path,
                config=self._config(steps),
                seed=77,
            )
            result = runner.run()
            summary = json.loads(
                (runner.output_dir / "summary.json").read_text(encoding="utf-8")
            )

            self.assertEqual(result, 1)
            self.assertFalse(summary["passed"])
            self.assertEqual(summary["blocking_failures"], ["fail"])
            self.assertEqual(len(summary["results"]), 1)
            self.assertFalse(marker.exists())

    def test_placeholders_and_environment_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "gate.toml"
            config_path.write_text("# test fixture\n", encoding="utf-8")
            output = root / "custom-evidence"
            step = gate.GateStep(
                "env",
                (
                    "{python}",
                    "-c",
                    "import os,sys; print(os.environ['CUSTOM']); print(sys.argv[1])",
                    "{run}:{seed}",
                ),
                True,
                1,
                (("CUSTOM", "root={root}"),),
            )
            runner = gate.ReleaseGateRunner(
                root=root,
                config_path=config_path,
                config=self._config((step,)),
                seed=42,
                output_root=output,
            )
            self.assertEqual(runner.run(), 0)
            log = (runner.output_dir / "env.log").read_text(encoding="utf-8")
            self.assertIn(f"root={root.resolve()}", log)
            self.assertIn("1:42", log)

    def test_clean_worktree_mode_requires_git_head(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "gate.toml"
            config_path.write_text("# test fixture\n", encoding="utf-8")
            config = gate.GateConfig(
                name="Clean gate",
                require_clean_worktree=True,
                output=Path("evidence"),
                environment=(),
                steps=(
                    gate.GateStep("pass", ("{python}", "-c", "pass"), True, 1, ()),
                ),
            )
            with self.assertRaises(gate.GateConfigurationError):
                gate.ReleaseGateRunner(
                    root=root,
                    config_path=config_path,
                    config=config,
                    seed=1,
                )


if __name__ == "__main__":
    unittest.main()
