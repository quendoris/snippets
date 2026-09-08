# Specification

## Runtime

Python 3.11+ is the intended runtime. The runner uses only the standard library.

## CLI

```text
--root PATH      audited project root; default current working directory
--config PATH    TOML manifest; relative paths resolve below --root
--output PATH    optional override for the evidence root
--seed INTEGER   optional recorded seed; otherwise a random 32-bit seed is generated
```

Exit status:

- `0` — all blocking steps passed; warnings may exist;
- `1` — a blocking step failed;
- `2` — manifest/precondition/output configuration failure;
- `130` — keyboard interruption.

## Manifest

The manifest requires one `[gate]` table and at least one `[[step]]` table.

### `[gate]`

Supported fields:

- `name`: non-empty string; default `release-gate`;
- `require_clean_worktree`: boolean; default `true`;
- `output`: path string; default `artifacts/release-gate`;
- `environment`: optional string-to-string inline/table mapping.

When clean-worktree mode is enabled, `git rev-parse HEAD` must succeed and `git status --porcelain` must be empty before the evidence directory is created.

### `[[step]]`

Required:

- `name`: unique filename-safe identifier matching `[A-Za-z0-9][A-Za-z0-9._-]*`;
- `command`: non-empty array of non-empty strings.

Optional:

- `blocking`: boolean, default `true`;
- `repeat`: integer >= 1, default `1`;
- `environment`: string-to-string mapping.

## Placeholders

Command elements and configured environment values use Python `str.format_map` with exactly these keys:

- `python`
- `seed`
- `output_dir`
- `root`
- `run`

Unknown placeholders are configuration errors when the affected step/environment is rendered. Literal braces must therefore be escaped as `{{` and `}}`.

## Execution

Steps execute in manifest order. Repetitions of a step execute consecutively before the next step.

`cwd` is the audited root. Commands are passed directly as argv to `subprocess.Popen` and are not evaluated by a shell.

stdout and stderr are combined, decoded as UTF-8 with replacement for invalid byte sequences, streamed to the parent terminal, and copied to the step log.

A process-start `OSError` is represented as return code `127` and follows the step's normal blocking policy.

On keyboard interruption the current child receives `terminate()`. The runner waits up to five seconds and then kills/waits for it before propagating interruption.

## Blocking semantics

After each result:

- pass → continue;
- failed non-blocking step → record warning, continue;
- failed blocking step → stop immediately and write final summaries.

Unexecuted later steps do not appear in the result list.

## Evidence

The runner creates a new directory:

```text
<output>/<UTC>-<commit-or-nogit>-seed-<seed>/
```

It contains:

- `metadata.json` before step execution;
- `<step>.log` or `<step>-NN.log` for repeated steps;
- `summary.json` after normal gate completion/failure;
- `summary.md` after normal gate completion/failure.

`summary.json` contains gate name, seed, Git commit/branch, blocking failures, warnings, and ordered result records. Each result records executed argv, blocking flag, return code, duration, log path and pass status.

## Git metadata

When available, metadata includes current commit, branch, dirty flag and raw `git status --porcelain` lines. Git-unavailable execution is permitted only when `require_clean_worktree = false`.

## Side effects

The runner writes only below its evidence output directory. Child commands may have arbitrary side effects; the runner does not sandbox them.
