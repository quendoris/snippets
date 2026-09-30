# GitHub Actions Push Run Discovery

A small deterministic selector for finding the **exact push-triggered GitHub
Actions run** that belongs to a branch, workflow and commit SHA.

It originated from a connector-diagnostics edge case: a high-level workflow
helper exposed pull-request-triggered runs but did not expose ordinary branch
`push` runs.  Read-only discovery through the GitHub Actions REST run listing
was able to identify the missing run, after which specialized Actions job/step/
log readers could be used normally.

## Connector exception

> **EXCEPTION — read-only discovery only**
>
> When the connected GitHub environment's high-level workflow-run helper omits
> push-triggered runs, a generic approved GitHub GET may read:
>
> ```text
> /repos/<owner>/<repo>/actions/runs?branch=<branch>&event=push&per_page=<N>
> ```
>
> This is not a general escape hatch for unsupported GitHub operations.  Use it
> only to discover a concrete `run_id`; then return to specialized Actions
> readers for jobs, steps, logs and artifacts.

The Python entrypoint in this snippet is deliberately offline.  It consumes the
JSON returned by that listing and selects exactly one run.  Network/auth behavior
therefore remains owned by the caller or connector.

## Example

Save the Actions run-listing payload as `runs.json`, then select the exact run:

```bash
python github-actions-push-run-discovery/src/push_run_discovery.py \
  --input runs.json \
  --branch experiment/puzzle-lazy-tree-v013 \
  --workflow "Test M4b normalized-defect nonblank child" \
  --head-sha ff1458ce0d358e0f9e72ecd216e2863e4b6bb12a \
  --json
```

To accept only a finished green run:

```bash
python github-actions-push-run-discovery/src/push_run_discovery.py \
  --input runs.json \
  --branch main \
  --workflow "CI" \
  --head-sha <full-commit-sha> \
  --require-completed \
  --require-success
```

The selector refuses ambiguous matches.  An old green run is never evidence for
a newer commit merely because workflow and branch names are the same.

See `docs/specification.md`, `docs/architecture.md`,
`docs/limitations.md` and `docs/connector-exception.md`.
