# Architecture

## Responsibility

The runner owns **execution evidence and failure semantics**, not a project's definition of quality.

A project supplies exact steps in TOML. The runner supplies:

- configuration validation;
- optional clean-Git precondition;
- immutable metadata capture for the invocation;
- deterministic seed propagation;
- exact argv execution without a shell;
- repeated steps;
- blocking versus informational failure handling;
- streamed per-step logs;
- JSON and Markdown summaries.

## Data flow

```text
release-gate.toml
      ↓
parse + validate
      ↓
collect Git/runtime metadata
      ↓
optional clean-worktree gate
      ↓
create isolated evidence directory
      ↓
for each declared step / repetition
      ↓
expand explicit placeholders
      ↓
subprocess argv + environment
      ↓
terminal + step.log
      ↓
StepResult
      ↓
blocking stop / continue
      ↓
summary.json + summary.md
```

## Why project commands live outside the runner

The source Persona Training Lab release gate encoded compileall, Ruff, its custom typing audit, mypy, pytest, localization audit, codebase statistics and package build directly in Python. Those commands are valid composition for that project but are not reusable architecture.

This extraction turns each command into manifest data. The runner therefore remains useful to C++, Python, Rust, mixed-language or non-build audit workflows as long as their checks can be invoked as processes.

## Exact argv boundary

Commands are TOML arrays and are passed directly to `subprocess.Popen`. No shell parsing or implicit pipeline/redirection occurs. This makes command boundaries inspectable in the manifest and avoids platform-specific quoting rules becoming hidden runner behavior.

`shlex.join()` is used only to make the recorded/displayed command readable; it is not used for execution.

## Evidence directory

The directory name contains UTC timestamp, the first 12 characters of the Git commit when available, and the seed. Creation uses `exist_ok=False`, so an existing evidence directory is never silently reused.

Metadata is written before any step executes. A blocking failure still produces summaries for every step that actually ran.

## Seed contract

The seed is evidence, not a promise that arbitrary child programs become deterministic. It is supplied through:

- `{seed}` placeholder;
- `PYTHONHASHSEED` when the caller has not already set it;
- `RELEASE_GATE_SEED`.

A child process must actually consume a relevant seed for its own randomness to become reproducible.

## Environment layering

Environment is composed in this order:

1. parent process environment;
2. `[gate].environment`;
3. current `[[step]].environment`;
4. runner evidence variables (`RELEASE_GATE_*`).

The step therefore overrides gate-level values. Runner evidence variables are authoritative.
