# Codebase Anatomy

`codebase-anatomy` reports the physical shape of a repository without pretending that directory names alone reveal architectural meaning.

It combines two kinds of evidence:

1. **automatic facts** — tracked files, language, physical/nonblank lines, measured or estimated code lines, bytes, structural roles;
2. **project-declared semantic groups** — explicit path groups such as `core`, `architecture`, `critical`, `critical-tests`, `operations`, or any other taxonomy the repository owner wants to measure.

The distinction is deliberate. A generic analyzer can identify Python or Markdown; it cannot reliably infer which lines embody an architectural decision or which subsystem is safety-critical.

## Status

Experimental (`0.1.0`). The output schema and language coverage may still evolve.

## Requirements

- Python 3.11+ (`tomllib` is used from the standard library);
- no third-party Python dependencies;
- Git is optional, but when available inside a repository the default source set is `git ls-files` for reproducible tracked-file accounting.

## Run

```bash
python codebase-anatomy/src/codebase_anatomy.py /path/to/repository
```

Machine-readable output:

```bash
python codebase-anatomy/src/codebase_anatomy.py /path/to/repository --json
```

Largest-file table size:

```bash
python codebase-anatomy/src/codebase_anatomy.py /path/to/repository --top 40
```

## Semantic repository groups

Create `codebase-anatomy.toml` in the analyzed repository root:

```toml
[settings]
ignore = [
  "vendor/**",
  "generated/**",
]

[[group]]
name = "core"
description = "Primary product implementation"
include = [
  "src/**/domain/**",
  "src/**/application/**",
]

[[group]]
name = "architecture"
include = [
  "src/**/runtime/**",
  "src/**/persistence/**",
  "docs/architecture/**",
]

[[group]]
name = "critical"
include = [
  "src/**/runtime_safety/**",
  "src/**/persistence/**",
]

[[group]]
name = "critical-tests"
include = [
  "tests/test_*_safety.py",
  "tests/test_runtime_*.py",
]
```

Groups may overlap. That is intentional: a file can be both `core` and `critical`, or both `architecture` and `documentation` when a project chooses such a taxonomy.

## What the report means

The human report contains:

- repository/Git metadata when available;
- structural-role totals;
- language totals;
- project-declared semantic-group totals;
- largest recognized text files;
- a methodology reminder.

JSON additionally includes per-file records and group definitions.

## Code-line methodology

Python is counted with the same basic method that motivated this snippet in Persona Training Lab: meaningful `tokenize` tokens are counted by source line while AST-recognized module/class/function docstring ranges are excluded.

Other supported programming languages currently use a conservative comment-stripped line estimate. That estimate is useful for engineering-size comparison but is **not parser-exact** and is not a complexity metric.

Documentation/configuration files keep physical and nonblank counts but intentionally report `code_lines = null`.

Read [`docs/specification.md`](docs/specification.md) and [`docs/limitations.md`](docs/limitations.md) before treating cross-language code-line totals as a scientific metric.

## Origin

The first implementation is distilled from Persona Training Lab's project-local `tools/codebase_stats.py`. PTL's release tool remains project-local; this snippet generalizes the reusable accounting idea rather than replacing PTL's release contract immediately.
