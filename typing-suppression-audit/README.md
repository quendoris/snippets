# Typing Suppression Audit

Small Python audit for finding type-checker suppressions that can silently hide typing failures.

It was extracted from the release tooling of `quendoris/persona-training-lab`, where a project-local script enforced a strict policy around `# type: ignore`, mypy file directives and configuration-level suppression. This snippet keeps the reusable scanner and makes the repository layout/policy explicit instead of retaining Persona Training Lab assumptions.

## What it detects

Source comments are tokenized, so marker-looking text inside Python strings is not reported.

Detected source markers:

- `# type: ignore`
- `# type: ignore[code]`
- `# mypy: ignore-errors`
- `# mypy: disable-error-code=...` and underscore spelling

Detected mypy-style configuration markers:

- `ignore_errors = true`
- `disable_error_code = ...`

By default every finding is blocking. A project may explicitly classify **coded** `# type: ignore[...]` comments under selected path prefixes as informational.

## Usage

From a repository root:

```bash
python typing-suppression-audit/src/typing_suppression_audit.py --root .
```

Defaults:

- code roots: `src`, `tests`, `tools`
- config candidates: `pyproject.toml`, `mypy.ini`, `.mypy.ini`, `setup.cfg`, `tox.ini`

Override them explicitly:

```bash
python typing-suppression-audit/src/typing_suppression_audit.py \
  --root . \
  --code-root package \
  --code-root verification \
  --config pyproject.toml
```

If a project intentionally permits narrow coded ignores in tests:

```bash
python typing-suppression-audit/src/typing_suppression_audit.py \
  --root . \
  --informational-coded-ignore-prefix tests/
```

Machine-readable report:

```bash
python typing-suppression-audit/src/typing_suppression_audit.py --root . --json
```

## Exit codes

- `0` — no blocking findings;
- `1` — one or more blocking suppressions were found;
- `2` — the audit could not read/tokenize an input.

## Why this is separate from mypy

A type checker answers whether the current code satisfies its configured rules. This audit answers a different question: **where has the repository explicitly told the checker not to report something?**

That distinction matters in release and review workflows because a successful mypy run can coexist with broad suppression directives.

See `docs/specification.md`, `docs/architecture.md`, and `docs/limitations.md` for the exact contract.
