from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shlex
import subprocess
import sys
import time
import tomllib
from typing import Iterable, Mapping


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class GateConfig:
    name: str
    require_clean_worktree: bool
    output: Path
    environment: tuple[tuple[str, str], ...]
    steps: tuple["GateStep", ...]


@dataclass(frozen=True, slots=True)
class GateStep:
    name: str
    command: tuple[str, ...]
    blocking: bool
    repeat: int
    environment: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class StepResult:
    name: str
    run: int
    command: tuple[str, ...]
    blocking: bool
    return_code: int
    duration_seconds: float
    log_path: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0


class GateConfigurationError(RuntimeError):
    pass


def _string_table(value: object, context: str) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise GateConfigurationError(f"{context} must be a TOML table")
    result: list[tuple[str, str]] = []
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise GateConfigurationError(f"{context} contains an invalid key")
        if not isinstance(item, str):
            raise GateConfigurationError(f"{context}.{key} must be a string")
        result.append((key, item))
    return tuple(sorted(result))


def load_config(path: Path) -> GateConfig:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise GateConfigurationError(f"cannot read gate config: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise GateConfigurationError(f"cannot parse gate config: {error}") from error

    gate = payload.get("gate")
    if not isinstance(gate, dict):
        raise GateConfigurationError("gate config requires a [gate] table")

    name = gate.get("name", "release-gate")
    if not isinstance(name, str) or not name.strip():
        raise GateConfigurationError("gate.name must be a non-empty string")

    require_clean = gate.get("require_clean_worktree", True)
    if not isinstance(require_clean, bool):
        raise GateConfigurationError("gate.require_clean_worktree must be boolean")

    raw_output = gate.get("output", "artifacts/release-gate")
    if not isinstance(raw_output, str) or not raw_output:
        raise GateConfigurationError("gate.output must be a non-empty path string")

    gate_env = _string_table(gate.get("environment"), "gate.environment")

    raw_steps = payload.get("step")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise GateConfigurationError("gate config requires at least one [[step]]")

    steps: list[GateStep] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_steps, start=1):
        context = f"step[{index}]"
        if not isinstance(raw, dict):
            raise GateConfigurationError(f"{context} must be a TOML table")
        step_name = raw.get("name")
        if not isinstance(step_name, str) or _SAFE_NAME.fullmatch(step_name) is None:
            raise GateConfigurationError(
                f"{context}.name must match {_SAFE_NAME.pattern!r}"
            )
        if step_name in seen:
            raise GateConfigurationError(f"duplicate step name: {step_name}")
        seen.add(step_name)

        command = raw.get("command")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) and item for item in command)
        ):
            raise GateConfigurationError(
                f"{context}.command must be a non-empty array of non-empty strings"
            )

        blocking = raw.get("blocking", True)
        if not isinstance(blocking, bool):
            raise GateConfigurationError(f"{context}.blocking must be boolean")

        repeat = raw.get("repeat", 1)
        if not isinstance(repeat, int) or isinstance(repeat, bool) or repeat < 1:
            raise GateConfigurationError(f"{context}.repeat must be an integer >= 1")

        steps.append(
            GateStep(
                name=step_name,
                command=tuple(command),
                blocking=blocking,
                repeat=repeat,
                environment=_string_table(raw.get("environment"), f"{context}.environment"),
            )
        )

    return GateConfig(
        name=name.strip(),
        require_clean_worktree=require_clean,
        output=Path(raw_output),
        environment=gate_env,
        steps=tuple(steps),
    )


def _git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def collect_metadata(root: Path, *, seed: int, config_path: Path) -> dict[str, object]:
    status = _git(root, "status", "--porcelain")
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "config": str(config_path),
        "commit": _git(root, "rev-parse", "HEAD") or None,
        "branch": _git(root, "branch", "--show-current") or "detached-or-unavailable",
        "dirty": bool(status.strip()),
        "dirty_paths": status.splitlines(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "seed": seed,
    }


def _expand(value: str, variables: Mapping[str, str]) -> str:
    try:
        return value.format_map(variables)
    except KeyError as error:
        raise GateConfigurationError(
            f"unknown placeholder {error.args[0]!r} in {value!r}"
        ) from error


def _render_command(
    step: GateStep,
    *,
    seed: int,
    output_dir: Path,
    run: int,
    root: Path,
) -> tuple[str, ...]:
    variables = {
        "python": sys.executable,
        "seed": str(seed),
        "output_dir": str(output_dir),
        "root": str(root),
        "run": str(run),
    }
    return tuple(_expand(part, variables) for part in step.command)


def _render_environment(
    pairs: Iterable[tuple[str, str]],
    *,
    seed: int,
    output_dir: Path,
    run: int,
    root: Path,
) -> dict[str, str]:
    variables = {
        "python": sys.executable,
        "seed": str(seed),
        "output_dir": str(output_dir),
        "root": str(root),
        "run": str(run),
    }
    return {key: _expand(value, variables) for key, value in pairs}


class ReleaseGateRunner:
    def __init__(
        self,
        *,
        root: Path,
        config_path: Path,
        config: GateConfig,
        seed: int,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        self.config_path = config_path.resolve()
        self.config = config
        self.seed = seed
        self.metadata = collect_metadata(
            self.root,
            seed=seed,
            config_path=self.config_path,
        )

        if config.require_clean_worktree:
            commit = self.metadata.get("commit")
            if not commit:
                raise GateConfigurationError(
                    "clean-worktree mode requires a Git worktree with a resolvable HEAD"
                )
            if self.metadata.get("dirty"):
                dirty = self.metadata.get("dirty_paths")
                shown = ", ".join(str(item) for item in dirty) if isinstance(dirty, list) else ""
                message = (
                    "release gate requires a clean Git worktree so evidence is tied "
                    "to the recorded commit"
                )
                if shown:
                    message += f"; dirty paths: {shown}"
                raise GateConfigurationError(message)

        base_output = output_root if output_root is not None else config.output
        if not base_output.is_absolute():
            base_output = self.root / base_output
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        commit = str(self.metadata.get("commit") or "nogit")[:12]
        self.output_dir = base_output / f"{stamp}-{commit}-seed-{seed}"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=False)
        except OSError as error:
            raise GateConfigurationError(
                f"cannot create isolated gate output: {self.output_dir}"
            ) from error
        self._write_json("metadata.json", self.metadata)

    def _write_json(self, name: str, payload: object) -> None:
        (self.output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _run_step(self, step: GateStep, run: int) -> StepResult:
        suffix = f"-{run:02d}" if step.repeat > 1 else ""
        result_name = f"{step.name}{suffix}"
        log_path = self.output_dir / f"{result_name}.log"
        command = _render_command(
            step,
            seed=self.seed,
            output_dir=self.output_dir,
            run=run,
            root=self.root,
        )
        command_text = shlex.join(command)
        print(f"[{result_name}] {command_text}")

        environment = os.environ.copy()
        environment.update(
            _render_environment(
                self.config.environment,
                seed=self.seed,
                output_dir=self.output_dir,
                run=run,
                root=self.root,
            )
        )
        environment.update(
            _render_environment(
                step.environment,
                seed=self.seed,
                output_dir=self.output_dir,
                run=run,
                root=self.root,
            )
        )
        environment.setdefault("PYTHONHASHSEED", str(self.seed))
        environment["RELEASE_GATE_SEED"] = str(self.seed)
        environment["RELEASE_GATE_OUTPUT_DIR"] = str(self.output_dir)
        environment["RELEASE_GATE_RUN"] = str(run)

        started = time.monotonic()
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"$ {command_text}\n\n")
            try:
                process = subprocess.Popen(
                    command,
                    cwd=self.root,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
            except OSError as error:
                log.write(f"runner could not start command: {error}\n")
                return_code = 127
            else:
                stdout = process.stdout
                if stdout is None:
                    process.kill()
                    process.wait()
                    raise RuntimeError(f"failed to capture output for step {step.name}")
                try:
                    with stdout:
                        for line in stdout:
                            print(line, end="")
                            log.write(line)
                except KeyboardInterrupt:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise
                return_code = process.wait()

        duration = round(time.monotonic() - started, 3)
        status = "PASS" if return_code == 0 else ("FAIL" if step.blocking else "WARN")
        print(f"[{result_name}] {status} in {duration:.3f}s")
        return StepResult(
            name=result_name,
            run=run,
            command=command,
            blocking=step.blocking,
            return_code=return_code,
            duration_seconds=duration,
            log_path=log_path.name,
        )

    def run(self) -> int:
        print(self.config.name)
        print(f"Output: {self.output_dir}")
        print(f"Seed: {self.seed}")
        results: list[StepResult] = []

        for step in self.config.steps:
            for run in range(1, step.repeat + 1):
                result = self._run_step(step, run)
                results.append(result)
                if result.blocking and not result.passed:
                    return self._finish(results)
        return self._finish(results)

    def _summary_payload(self, results: Iterable[StepResult]) -> dict[str, object]:
        items = tuple(results)
        blocking_failures = [item.name for item in items if item.blocking and not item.passed]
        warnings = [item.name for item in items if not item.blocking and not item.passed]
        return {
            "passed": not blocking_failures,
            "gate": self.config.name,
            "seed": self.seed,
            "commit": self.metadata.get("commit"),
            "branch": self.metadata.get("branch"),
            "blocking_failures": blocking_failures,
            "warnings": warnings,
            "results": [
                {**asdict(item), "passed": item.passed}
                for item in items
            ],
        }

    def _finish(self, results: Iterable[StepResult]) -> int:
        payload = self._summary_payload(results)
        self._write_json("summary.json", payload)
        self._write_markdown(payload)
        failures = payload["blocking_failures"]
        warnings = payload["warnings"]
        if failures:
            print("RELEASE GATE: FAIL")
            print("Blocking failures: " + ", ".join(str(item) for item in failures))
            return 1
        if warnings:
            print("RELEASE GATE: PASS WITH WARNINGS")
            print("Warnings: " + ", ".join(str(item) for item in warnings))
        else:
            print("RELEASE GATE: PASS")
        return 0

    def _write_markdown(self, payload: Mapping[str, object]) -> None:
        lines = [
            f"# {self.config.name}",
            "",
            f"- Result: **{'PASS' if payload['passed'] else 'FAIL'}**",
            f"- Commit: `{payload.get('commit') or 'unavailable'}`",
            f"- Branch: `{payload.get('branch') or 'unavailable'}`",
            f"- Seed: `{self.seed}`",
            f"- Dirty worktree: `{self.metadata.get('dirty', False)}`",
            "",
            "| Step | Blocking | Result | Seconds | Log |",
            "|---|---:|---:|---:|---|",
        ]
        raw_results = payload.get("results")
        if isinstance(raw_results, list):
            for raw in raw_results:
                if not isinstance(raw, dict):
                    continue
                lines.append(
                    "| {name} | {blocking} | {status} | {seconds:.3f} | `{log}` |".format(
                        name=raw.get("name", "?"),
                        blocking="yes" if raw.get("blocking") else "no",
                        status="PASS" if raw.get("passed") else "FAIL",
                        seconds=float(raw.get("duration_seconds", 0.0)),
                        log=raw.get("log_path", ""),
                    )
                )
        warnings = payload.get("warnings")
        if isinstance(warnings, list) and warnings:
            lines.extend(("", "## Informational failures", ""))
            lines.extend(f"- `{item}`" for item in warnings)
        lines.append("")
        (self.output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an argv-defined reproducible release/audit gate.",
    )
    parser.add_argument("--config", type=Path, default=Path("release-gate.toml"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    try:
        config = load_config(config_path)
        runner = ReleaseGateRunner(
            root=root,
            config_path=config_path,
            config=config,
            seed=seed,
            output_root=args.output,
        )
        return runner.run()
    except GateConfigurationError as error:
        print(f"Release gate configuration error: {error}")
        return 2
    except KeyboardInterrupt:
        print("\nRelease gate interrupted. Existing per-step logs were preserved.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
