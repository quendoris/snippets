# Connector exception: discovering push-triggered Actions runs

## The observed exception

In the originating development workflow, the connected GitHub helper used for
commit workflow runs had a narrower behavior: it surfaced pull-request-triggered
runs but could return no runs for ordinary branch `push` workflows.

The connected GitHub environment also exposed a generic approved **read** action
for GitHub resources.  Reading the documented Actions run collection made the
missing push runs visible:

```text
GET /repos/<owner>/<repo>/actions/runs
    ?branch=<branch>
    &event=push
    &per_page=<N>
```

This was used successfully to discover the concrete `run_id`.

## Safe operational sequence

1. Try the specialized/high-level workflow helper first.
2. If its known trigger limitation hides push runs, use the generic GitHub GET
   only for the Actions run-listing resource.
3. Filter by the exact branch, workflow display name and **full head SHA**.
4. Inspect `status` and `conclusion`; do not reuse an older green run as
   evidence for current head.
5. With the discovered `run_id`, switch back to specialized readers:
   - workflow run jobs;
   - job steps;
   - job logs;
   - run artifacts.
6. Report CI green only when the intended run is `completed/success`.

## Why this is explicitly an exception

The generic GET is broader than the high-level helper, so using it silently as
the default would hide an important tool-contract boundary.

The exception is acceptable here because all of the following hold:

- operation is read-only;
- resource is the documented GitHub Actions run collection;
- access still uses the already-authorized connected GitHub account;
- the generic read is used only to discover IDs;
- specialized Actions readers resume immediately afterward.

This document does **not** claim that every generic REST read exposed by a
connector should be used, and says nothing about unsupported writes.

## Practical diagnostics

When a run is found but still executing, prefer checking job/step state before
requesting logs.  Some log endpoints may return unavailable/not-found while the
job is still in progress.  Treat that as "log not materialized yet" unless the
workflow itself has completed with failure.
