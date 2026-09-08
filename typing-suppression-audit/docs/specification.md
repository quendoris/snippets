# Specification

## Runtime

Python 3.11+ is the intended runtime. The implementation uses only the standard library.

## Inputs

The CLI accepts:

- `--root PATH` — repository/display root; defaults to the current working directory;
- repeated `--code-root PATH` — directories recursively scanned for `*.py`;
- repeated `--config PATH` — individual configuration files;
- repeated `--informational-coded-ignore-prefix PREFIX` — repository path prefixes under which coded `# type: ignore[...]` findings are informational;
- `--json` — machine-readable output.

When `--code-root` is omitted, `src`, `tests`, and `tools` are used. Missing code roots are ignored.

When `--config` is omitted, the following candidates are inspected when present:

- `pyproject.toml`
- `mypy.ini`
- `.mypy.ini`
- `setup.cfg`
- `tox.ini`

Missing config candidates are ignored.

Relative paths are resolved below `--root`. Absolute paths are accepted but may produce absolute display paths when they lie outside the root.

## Source detection

Only Python `COMMENT` tokens are considered.

The scanner recognizes:

1. `# type: ignore` with or without a bracketed error-code list;
2. `# mypy: ignore-errors`, case-insensitive;
3. `# mypy: disable-error-code...` and `disable_error_code...`, case-insensitive.

At most one finding is emitted per comment token.

## Configuration detection

Each config file is decoded as UTF-8 and scanned line-by-line.

Recognized lines are:

- `ignore_errors = true`, with optional surrounding whitespace and trailing `#` comment;
- any assignment beginning `disable_error_code =`, case-insensitive.

The scanner does not interpret configuration sections or inheritance.

## Finding ordering

Findings are sorted by:

1. normalized display path;
2. line number;
3. finding kind.

This ordering is deterministic for the same input bytes and path set.

## Classification

Default severity is blocking.

A finding becomes informational only when all are true:

- its kind is `type_ignore`;
- its text contains a bracketed error-code list, e.g. `# type: ignore[arg-type]`;
- its normalized repository path starts with one of the explicitly supplied informational prefixes.

No other suppression is downgraded by this mechanism.

## JSON output

The JSON object contains:

- `passed` — true when blocking count is zero;
- `finding_count`;
- `blocking_finding_count`;
- `informational_finding_count`;
- `findings` — ordered finding objects containing `path`, `line`, `kind`, `text`, and `blocking`.

Operational failure with `--json` emits an object containing `passed: false` and `error`.

## Exit status

- `0`: zero blocking findings;
- `1`: at least one blocking finding;
- `2`: input read/decode/tokenization failure.

## Side effects

The snippet performs no writes and no network access.
