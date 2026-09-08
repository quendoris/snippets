# Architecture

## Boundary

The snippet has one responsibility: inventory explicit Python typing suppressions and classify them according to a small caller-supplied policy.

It does not invoke mypy, pyright, a formatter, or a build system.

## Data flow

```text
repository root
    ↓
selected Python roots ──→ tokenize comments ──→ source findings
    ↓
selected config files ──→ line patterns ─────→ config findings
    ↓
normalized finding list
    ↓
policy classification
    ↓
text / JSON / exit code
```

## Why tokenize Python comments

A raw regular-expression search across source files produces false positives for strings such as documentation examples or test fixtures containing `# type: ignore` text.

The scanner therefore uses Python's `tokenize` module and applies suppression patterns only to `COMMENT` tokens. This keeps the implementation dependency-free while matching the syntactic location where Python typing directives live.

## Configuration scanning

Mypy configuration can appear in formats that are not all represented by one standard parser in the Python standard library. The reusable behavior required here is deliberately narrower: inventory exact suppression assignments. Config files are therefore scanned line-by-line for the supported assignments instead of interpreting the complete surrounding configuration format.

## Policy separation

Detection and severity are separate operations.

The scanner reports facts. The classifier decides whether a fact blocks the audit.

Default policy is conservative: every finding blocks. The only built-in downgrade mechanism is explicit path-prefix allowance for **coded** `# type: ignore[...]` comments. An uncoded `# type: ignore`, file-wide mypy directive, or configuration-level suppression remains blocking even under those prefixes.

This reflects the reusable part of the original Persona Training Lab rule without making that project's `tests/` policy universal.

## Error boundary

Unreadable UTF-8 inputs and Python tokenization failures are operational errors, not clean audit results. The CLI reports them with exit code `2` rather than pretending the repository passed.
