# Specification

## Invocation

```text
python src/codebase_anatomy.py [PATH] [--config FILE] [--json] [--top N]
```

`PATH` defaults to the current directory.

If `PATH` is inside a Git repository, analysis is rooted at that repository's top level.

## Configuration discovery

Unless `--config` is supplied, the tool looks for:

```text
<analysis-root>/codebase-anatomy.toml
```

Absence of the file is valid and means no project-declared semantic groups are applied.

### `[settings]`

Supported field:

```toml
[settings]
ignore = ["vendor/**", "generated/**"]
```

Configured ignores are appended to built-in ignores.

### `[[group]]`

Required:

- `name`: non-empty string;
- `include`: non-empty array of glob strings.

Optional:

- `exclude`: array of glob strings;
- `description`: string.

Example:

```toml
[[group]]
name = "critical"
include = ["src/**/persistence/**"]
exclude = ["src/**/persistence/generated/**"]
```

Matching uses `fnmatch` against POSIX-style repository-relative paths.

## Source selection

### Git mode

When Git repository discovery succeeds:

```text
source_mode = "git-tracked"
```

Files come from:

```text
git ls-files -z
```

### Filesystem mode

When Git discovery fails:

```text
source_mode = "filesystem"
```

Files are discovered recursively below the requested directory.

## Recognized file record

Each recognized UTF-8 file produces:

```json
{
  "path": "src/example.py",
  "language": "Python",
  "role": "production-code",
  "physical_lines": 120,
  "nonblank_lines": 101,
  "code_lines": 77,
  "code_method": "python-tokenize-minus-ast-docstrings",
  "bytes_count": 3890,
  "groups": ["core", "critical"]
}
```

For documentation/configuration/presentation files where no code-line algorithm is claimed:

```text
code_lines = null
code_method = null
```

## Metrics

### Physical lines

`physical_lines` is the number of entries returned by Python `str.splitlines()` for the UTF-8 decoded file.

### Nonblank lines

A line is nonblank when `line.strip()` is non-empty.

### Python code lines

Python code lines are unique source-line numbers that contain meaningful tokenizer tokens after excluding:

- comments;
- `ENCODING`;
- `ENDMARKER`;
- `INDENT`;
- `DEDENT`;
- `NEWLINE`;
- `NL`;
- AST-recognized module/class/function docstring ranges.

If Python tokenization fails, the implementation currently falls back to nonblank-line counting for that source.

### Approximate code lines

Other supported programming languages use line-oriented removal of obvious comment-only/block-comment content.

The metric deliberately does not parse string literals or language grammar. It must be treated as an engineering-size estimate.

## Structural roles

Classification order is significant:

1. documentation;
2. tests;
3. engineering support;
4. configuration;
5. production code;
6. asset/presentation;
7. other text.

A Python file under `tests/` is therefore a test before it is generic production code.

## Aggregation

`totals`, `roles`, `languages`, and `semantic_groups` aggregate these integer fields:

- `files`
- `physical_lines`
- `nonblank_lines`
- `code_lines`
- `bytes`

Semantic-group aggregates overlap when files belong to multiple groups.

## JSON top-level shape

```text
metadata
methodology
totals
roles
languages
semantic_groups
group_definitions
files
```

### `metadata`

Contains:

- absolute analysis root;
- source mode;
- branch when Git can report one;
- full commit SHA when Git can report one;
- dirty-worktree boolean when Git status is available.

A dirty report is still produced. Consumers decide whether dirty state is acceptable for their workflow.

## Exit behavior

- `0`: analysis completed;
- `2`: argument/configuration error.

Unexpected I/O/runtime failures are not currently normalized into a dedicated exit-code taxonomy and may surface as Python exceptions.

## Side effects

The snippet is read-only with respect to the analyzed repository.

It invokes Git read commands when available but does not run Git mutation commands.
