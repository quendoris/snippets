# Latest Preview Scheduler

A small C++17 scheduling state machine for interactive work where previews arrive faster than expensive background computation can finish.

It was extracted from AERIS Desktop's scene controller. During globe dragging, AERIS may receive many preview camera requests while one geometry build is still running. Cancel/restart on every mouse event wastes work; queueing every event produces stale latency. The policy used in AERIS keeps at most one preview in flight plus the newest pending preview.

Verified/release-time requests have different semantics: they are authoritative, discard pending previews, and invalidate older in-flight work so stale results cannot be applied afterwards.

## Policy

- idle + preview -> start now;
- running preview + preview -> replace the single pending preview;
- preview completion -> start the newest pending preview, if any;
- verified request -> discard pending preview and preempt current work;
- preview while verified work runs -> preempt verified work to restore interactive response;
- completion carrying an old generation -> reject as stale;
- cancel -> clear pending work and invalidate the active generation.

The snippet is deliberately Qt-free. It does not create threads or cancel them itself; callers map `preempt_and_start`, generation IDs, and completion decisions onto their own worker system.

See `docs/architecture.md`, `docs/specification.md`, and `docs/limitations.md` for the exact state-machine contract.
