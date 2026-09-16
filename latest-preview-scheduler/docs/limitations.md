# Limitations

## Scheduling policy, not a thread pool

The snippet does not start, stop, join or own worker threads. `preempt_and_start` means the caller should invalidate/cancel the current worker using whatever mechanism its runtime provides and launch the returned request.

## Cancellation may be cooperative

Generation rejection prevents a stale completion from being accepted, but it does not stop obsolete computation from consuming CPU. The consuming worker should still check a cancellation token when practical.

## Exactly two quality classes

Version `0.1.0` models the distinction that existed in AERIS: interactive preview versus authoritative verified work. It is not a general priority queue.

## Single pending preview

This is deliberate coalescing. Every intermediate preview except the newest pending one may be dropped. Do not use this policy when every request represents a required side effect or durable transaction.

## Caller supplies completion quality

The completion API receives the quality of the task that finished. The caller must preserve the launch metadata and return it with the same generation. The generation check protects against stale work, not malformed caller metadata.

## Generation wraparound

The generation is a `uint64_t` and no special wraparound handling is implemented. For ordinary application lifetimes this is effectively unreachable, but the implementation does not claim a mathematical no-wrap guarantee.

## Request type requirements

`Request` must be movable and suitable for storage in `std::optional`. Copyability is not required by the policy itself.
