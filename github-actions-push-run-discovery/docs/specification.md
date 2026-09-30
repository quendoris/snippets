# Specification

## Runtime

Python 3.11+; standard library only.

## Input

`--input PATH` must contain JSON whose root object has a `workflow_runs`
array compatible with GitHub Actions' "List workflow runs for a repository"
response.

Each candidate run must provide the fields needed by the requested filters:

- `id`
- `name`
- `event`
- `head_branch`
- `head_sha`
- `status`
- `conclusion`

Unknown additional fields are preserved in the selected result.

## Required filters

- `--branch NAME`
- `--workflow NAME`
- `--head-sha SHA`

Selection always requires:

```text
event == "push"
head_branch == --branch
name == --workflow
head_sha == --head-sha
```

SHA comparison is exact after lowercase normalization.  Prefix matching is not
performed.

## Optional filters

`--require-completed` additionally requires:

```text
status == "completed"
```

`--require-success` implies completed and additionally requires:

```text
conclusion == "success"
```

## Output

Without `--json`, stdout is:

```text
<run_id>
```

With `--json`, stdout contains a normalized JSON object with:

- `id`
- `name`
- `event`
- `head_branch`
- `head_sha`
- `status`
- `conclusion`
- `html_url` when present

## Exit status

- `0` — exactly one run matched;
- `1` — no run matched;
- `2` — invalid input/arguments or more than one run matched.

Ambiguity is an error rather than an implicit latest/first selection.

## Side effects

The snippet only reads its input file and writes stdout/stderr.
