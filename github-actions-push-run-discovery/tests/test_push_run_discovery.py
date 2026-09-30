from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "push_run_discovery.py"
)
SPEC = importlib.util.spec_from_file_location(
    "push_run_discovery",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def run(
    run_id: int,
    *,
    name: str = "CI",
    event: str = "push",
    branch: str = "main",
    sha: str = "a" * 40,
    status: str = "completed",
    conclusion: str | None = "success",
):
    return {
        "id": run_id,
        "name": name,
        "event": event,
        "head_branch": branch,
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "html_url": f"https://example.invalid/runs/{run_id}",
    }


class SelectRunTests(unittest.TestCase):
    def test_selects_exact_push_head(self):
        payload = {
            "workflow_runs": [
                run(1, sha="b" * 40),
                run(2, sha="a" * 40),
                run(3, event="pull_request", sha="a" * 40),
            ]
        }
        selected = MODULE.select_run(
            payload,
            branch="main",
            workflow="CI",
            head_sha="a" * 40,
        )
        self.assertEqual(selected["id"], 2)

    def test_never_uses_old_green_run_for_new_head(self):
        payload = {
            "workflow_runs": [
                run(10, sha="1" * 40),
            ]
        }
        selected = MODULE.select_run(
            payload,
            branch="main",
            workflow="CI",
            head_sha="2" * 40,
        )
        self.assertIsNone(selected)

    def test_require_success_rejects_in_progress(self):
        payload = {
            "workflow_runs": [
                run(
                    4,
                    status="in_progress",
                    conclusion=None,
                )
            ]
        }
        selected = MODULE.select_run(
            payload,
            branch="main",
            workflow="CI",
            head_sha="a" * 40,
            require_success=True,
        )
        self.assertIsNone(selected)

    def test_ambiguous_exact_match_is_error(self):
        payload = {
            "workflow_runs": [
                run(5),
                run(6),
            ]
        }
        with self.assertRaises(MODULE.DiscoveryError):
            MODULE.select_run(
                payload,
                branch="main",
                workflow="CI",
                head_sha="a" * 40,
            )

    def test_branch_and_workflow_are_exact(self):
        payload = {
            "workflow_runs": [
                run(7, branch="dev"),
                run(8, name="Other"),
            ]
        }
        selected = MODULE.select_run(
            payload,
            branch="main",
            workflow="CI",
            head_sha="a" * 40,
        )
        self.assertIsNone(selected)

    def test_invalid_payload_is_error(self):
        with self.assertRaises(MODULE.DiscoveryError):
            MODULE.select_run(
                {"workflow_runs": "not-a-list"},
                branch="main",
                workflow="CI",
                head_sha="a" * 40,
            )


if __name__ == "__main__":
    unittest.main()
