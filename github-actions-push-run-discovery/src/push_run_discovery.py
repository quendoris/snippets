from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


class DiscoveryError(ValueError):
    pass


def _runs(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise DiscoveryError("payload root must be an object")
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise DiscoveryError("payload.workflow_runs must be an array")
    if not all(isinstance(run, dict) for run in runs):
        raise DiscoveryError("every workflow_runs item must be an object")
    return runs


def select_run(
    payload: object,
    *,
    branch: str,
    workflow: str,
    head_sha: str,
    require_completed: bool = False,
    require_success: bool = False,
) -> dict[str, Any] | None:
    if not branch:
        raise DiscoveryError("branch must be non-empty")
    if not workflow:
        raise DiscoveryError("workflow must be non-empty")
    if not head_sha:
        raise DiscoveryError("head_sha must be non-empty")

    wanted_sha = head_sha.lower()
    if require_success:
        require_completed = True

    matches: list[dict[str, Any]] = []
    for run in _runs(payload):
        if run.get("event") != "push":
            continue
        if run.get("head_branch") != branch:
            continue
        if run.get("name") != workflow:
            continue

        candidate_sha = run.get("head_sha")
        if not isinstance(candidate_sha, str):
            continue
        if candidate_sha.lower() != wanted_sha:
            continue

        if require_completed and run.get("status") != "completed":
            continue
        if require_success and run.get("conclusion") != "success":
            continue
        matches.append(run)

    if not matches:
        return None
    if len(matches) != 1:
        ids = [run.get("id") for run in matches]
        raise DiscoveryError(
            f"ambiguous workflow run match: {len(matches)} candidates ids={ids}"
        )
    return matches[0]


def normalized_output(run: dict[str, Any]) -> dict[str, Any]:
    out = {
        "id": run.get("id"),
        "name": run.get("name"),
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
    }
    if "html_url" in run:
        out["html_url"] = run.get("html_url")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--head-sha", required=True)
    ap.add_argument("--require-completed", action="store_true")
    ap.add_argument("--require-success", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        run = select_run(
            payload,
            branch=args.branch,
            workflow=args.workflow,
            head_sha=args.head_sha,
            require_completed=args.require_completed,
            require_success=args.require_success,
        )
    except (OSError, json.JSONDecodeError, DiscoveryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if run is None:
        print("no matching push workflow run", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(normalized_output(run), indent=2, sort_keys=True))
    else:
        print(run.get("id"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
