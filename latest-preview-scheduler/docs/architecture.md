# Architecture

## Origin

AERIS Desktop builds map geometry on a background worker. Pointer movement can produce preview requests much faster than a geometry build completes. The project therefore stopped treating every request as an independent queued job.

The extracted state machine separates three concerns:

```text
request stream
    ↓
latest-preview scheduling policy
    ↓
launch / queue / preempt decisions
    ↓
caller-owned worker system
```

## Bounded preview pressure

While a preview is running, another preview does not cancel it immediately. Instead it occupies one pending slot. A later preview replaces that pending value. The worker queue is therefore bounded to:

- one in-flight preview;
- one newest pending preview.

When the in-flight preview completes, the newest pending request starts. Intermediate camera positions are intentionally discarded.

## Generations

Every actual launch receives a monotonically increasing generation. Preemption/cancel also advances the generation. Completion is accepted only when its generation matches the current active generation.

This lets the caller use cooperative cancellation without trusting it to stop instantly: a late result can arrive, but the state machine rejects it as stale.

## Verified work

A verified request represents an authoritative final state rather than another intermediate preview. It clears the pending preview and invalidates current work before launching.

A new user preview is allowed to preempt verified work. That mirrors the AERIS interaction rule that visible responsiveness to a new drag takes priority over finishing geometry for the previous release-time camera.

## Pure policy boundary

The snippet has no Qt dependency, owns no threads and performs no callbacks. It only returns decisions. The consumer decides how to set cancellation tokens, clear queues, launch tasks, and deliver accepted results.
