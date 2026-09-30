# Limitations

## Discovery only

The snippet does not fetch GitHub itself.  It parses an already-acquired Actions
run-listing payload.  Authentication, network retries, pagination and API rate
limits belong to the caller.

## Connector exception is intentionally narrow

The generic GitHub GET described in `docs/connector-exception.md` exists to
work around a narrower high-level **read** helper when discovering push runs.

It must not be generalized into:

- arbitrary GitHub endpoint access;
- mutation/write fallback;
- bypassing connector authorization;
- assuming unsupported resource families are safe merely because a REST path
  exists.

After discovery, prefer specialized Actions readers for jobs, steps, logs and
artifacts.

## Pagination

A single Actions listing may not contain the desired run.  The caller must
request enough records or follow pagination before treating "not found" as
authoritative.

## Workflow display names

The selector matches the run's `name` exactly.  Repositories that rename
workflow display names must use the name present in the returned payload.

## Reruns

GitHub may represent reruns with the same workflow/branch/head SHA.  If the
provided payload contains multiple candidates satisfying every requested filter,
this version rejects the result as ambiguous instead of guessing by
`run_attempt` or creation time.

## Logs may lag run state

Discovering a run/job does not guarantee logs are immediately materialized.
A temporary 404/empty log result for an in-progress job should not be interpreted
as a solver or CI failure.
