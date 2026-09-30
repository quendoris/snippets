# Architecture

## Responsibility

This snippet owns one narrow problem: select the exact GitHub Actions
**push-triggered workflow run** represented by an already-acquired
`/actions/runs` JSON payload.

It does not call GitHub, manage authentication, start workflows, mutate
repositories or fetch logs.

## Data flow

```text
GitHub Actions workflow-runs JSON
        ↓
validate payload shape
        ↓
event == "push"
        ↓
exact branch match
        ↓
exact workflow-name match
        ↓
exact head_sha match
        ↓
optional completed/success filters
        ↓
0 matches  -> not found
1 match    -> selected run
>1 matches -> ambiguous, reject
```

The exact SHA filter is intentionally first-class.  Workflow name plus branch is
not enough evidence because multiple historical runs may exist.

## Connector integration exception

The originating integration used a high-level workflow helper first.  When that
helper's contract exposed only pull-request-triggered runs, read-only discovery
fell back to the generic connected GitHub GET wrapper for the documented Actions
REST collection:

```text
/repos/<owner>/<repo>/actions/runs?branch=<branch>&event=push&per_page=<N>
```

Once a concrete `run_id` exists, the integration returns to specialized
Actions readers for run jobs, job steps, logs and artifacts.

This separation is deliberate:

- generic GET is discovery-only;
- specialized tools own run/job/log interpretation;
- no generic write/mutation fallback is implied.

## Determinism

Given identical input JSON and CLI filters, selection is deterministic.  The
snippet never chooses "latest" as a substitute for exact identity.
