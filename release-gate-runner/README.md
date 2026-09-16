# Release Gate Runner

A small manifest-driven runner for reproducible release and audit gates.

It was extracted from Persona Training Lab's `tools/release_gate.py`. The original tool correctly owned evidence, Git cleanliness, deterministic seed propagation, per-step logs and blocking/non-blocking failure semantics, but also hard-coded Persona Training Lab's exact Ruff/mypy/pytest/i18n/build composition. This snippet keeps the reusable orchestration and moves project composition into TOML.

## Example

Create `release-gate.toml` in the project being audited:

```toml
[gate]
name = "Example release audit"
require_clean_worktree = true
output = "artifacts/release-gate"

environment = { QT_QPA_PLATFORM = "offscreen" }

[[step]]
name = "compile"
command = ["{python}", "-m", "compileall", "-q", "src", "tests"]

[[step]]
name = "tests"
command = ["{python}", "-m", "pytest", "-q"]
repeat = 3

[[step]]
name = "optional-report"
command = ["{python}", "tools/report.py", "--output", "{output_dir}/report.json"]
blocking = false
```

Run it:

```bash
python release-gate-runner/src/release_gate_runner.py \
  --root /path/to/project \
  --config release-gate.toml
```

For a reproducible rerun, supply the recorded seed:

```bash
python release-gate-runner/src/release_gate_runner.py \
  --root /path/to/project \
  --config release-gate.toml \
  --seed 123456789
```

## Evidence

Each invocation creates an isolated directory containing:

- `metadata.json` — Git/Python/platform/seed metadata;
- one `.log` per executed step/run;
- `summary.json` — machine-readable outcome;
- `summary.md` — compact human report.

The runner streams child output to the terminal while writing the same output to the step log.

## Failure semantics

A failed blocking step stops the gate immediately and exits `1` after writing summaries. A failed non-blocking step is recorded as a warning and execution continues.

Configuration errors exit `2`. Keyboard interruption exits `130`; logs already written remain on disk.

## Placeholders

Each argv element and configured environment value may use:

- `{python}` — current Python executable;
- `{seed}` — recorded gate seed;
- `{output_dir}` — isolated evidence directory;
- `{root}` — audited project root;
- `{run}` — 1-based repetition number for the current step.

Commands are executed as exact argv arrays with `shell=False` semantics; the manifest is not a shell script.

See `docs/specification.md`, `docs/architecture.md`, and `docs/limitations.md` for the precise contract.
