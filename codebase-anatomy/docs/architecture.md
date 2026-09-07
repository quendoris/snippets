# Architecture

## Goal

`codebase-anatomy` separates **facts a generic analyzer can observe** from **semantic classifications only the repository owner can define reliably**.

The architecture therefore has two parallel layers:

```text
repository
   │
   ├─ tracked/file-system source selection
   │
   ├─ automatic file facts
   │    ├─ language
   │    ├─ structural role
   │    ├─ physical lines
   │    ├─ nonblank lines
   │    ├─ code-line method/value
   │    └─ byte size
   │
   └─ project-declared semantic groups
        ├─ core
        ├─ architecture
        ├─ critical
        ├─ critical-tests
        └─ any project-defined group
```

The final report joins these layers without pretending that semantic groups are mutually exclusive.

## Source selection

When the analysis path is inside a Git repository, the tool resolves the Git top level and reads `git ls-files -z`. This makes the default report correspond to version-controlled inputs rather than arbitrary editor caches, build products, or local generated files.

When Git is unavailable or the path is not a Git repository, the tool falls back to recursive filesystem discovery and applies default/configured ignore globs.

The source mode is recorded in output as either:

- `git-tracked`
- `filesystem`

## File recognition

Recognition is intentionally explicit. A file contributes only when its exact filename or suffix maps to a known language/text family.

Unknown or non-UTF-8 files are skipped rather than guessed.

This avoids a misleading claim that arbitrary binary/generated content has been measured accurately.

## Structural roles

The current built-in role classifier is path/language based and intentionally small:

- `documentation`
- `tests`
- `engineering-support`
- `configuration`
- `production-code`
- `asset-or-presentation`
- `other-text`

The classifier is a convenience taxonomy, not an architectural truth model. Project-specific meanings belong in semantic groups.

## Code-line strategies

### Python

Python uses token-aware counting:

1. parse the source AST when possible;
2. identify module/class/function docstring ranges;
3. tokenize source;
4. ignore comments, structural newline/indent tokens, encoding/end markers;
5. count source lines containing remaining meaningful tokens and not belonging to docstring ranges.

This produces a stronger measure than physical LOC while still remaining a size metric rather than complexity analysis.

### Other programming languages

The first reusable version applies a conservative line-comment/block-comment stripping estimate for supported languages.

This code path intentionally does not pretend to be a full parser. The report records `code_method = "comment-stripped-estimate"` for those files.

A future language adapter may replace an estimate with parser-aware counting without changing the repository semantic-group model.

## Semantic groups

Semantic groups are loaded from `codebase-anatomy.toml`.

A group has:

- `name`
- one or more `include` globs
- zero or more `exclude` globs
- optional `description`

Membership is evaluated independently per group. Therefore groups may overlap.

This is essential for useful engineering questions. For example:

- persistence code may be both `core` and `critical`;
- a runtime-safety test may be both `tests` and `critical-tests`;
- architecture documentation may be both structural `documentation` and semantic `architecture`.

## Aggregation

Per-file records are aggregated three ways:

1. by structural role;
2. by language;
3. by declared semantic group.

All three aggregations expose:

- file count;
- physical lines;
- nonblank lines;
- measured/estimated code lines;
- byte count in JSON.

Because semantic groups overlap, their totals must never be summed as though they partition the repository.

## Output boundary

Human output is intended for interactive engineering review.

JSON output is the stable integration surface for downstream dashboards, historical trend capture, release evidence, or documentation generation.

The current version does not write files or mutate the analyzed repository.
