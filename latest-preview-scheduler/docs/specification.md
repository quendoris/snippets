# Specification

## Runtime

C++17 standard library only. The implementation is header-only.

## Types

`Quality` has two values:

- `preview` — interactive/intermediate work;
- `verified` — authoritative release-time work.

`RequestAction` has three values:

- `start` — launch the returned request without preemption;
- `queue_latest_preview` — do not launch now; the pending preview slot was replaced;
- `preempt_and_start` — invalidate/cancel the caller's current worker, then launch the returned request.

Each actual launch contains the request value, quality and a generation ID.

## Request transitions

### Idle

Any request launches immediately with a new generation and returns `start`.

### Preview running + preview requested

The new request replaces the one pending preview slot. No generation changes and no worker launch is returned. The action is `queue_latest_preview`.

### Verified running + preview requested

The running generation is invalidated, then the preview launches under a new generation. The action is `preempt_and_start`.

### Any running work + verified requested

The pending preview slot is cleared. The running generation is invalidated and the verified request launches under a new generation. The action is `preempt_and_start`.

## Completion transitions

`complete(generation, quality)` accepts a completion only when work is currently marked running and the supplied generation equals the current generation.

A stale completion returns `accepted = false` and cannot launch more work.

When an accepted preview completes and a pending preview exists, that newest pending request launches immediately under a fresh generation.

An accepted completion without such a pending preview leaves the scheduler idle.

## Cancel

`cancel()` clears the pending preview, advances the generation and leaves no work marked running. A later completion from the old generation is stale.

## Invariants

- At most one pending preview is stored.
- A later preview replaces an older pending preview.
- A verified request cannot be followed by an older pending preview.
- A completion from an invalidated generation cannot mutate scheduling state.
- Every launch gets a generation distinct from the generation it preempted.
