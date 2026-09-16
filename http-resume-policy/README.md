# HTTP Resume Policy

A small C++17 decision layer for safe HTTP byte-range resume.

This snippet was extracted from AERIS Desktop's verified Natural Earth acquisition path. The original downloader needed to resume `.part` files without ever appending a complete `200 OK` response to an old prefix, accepting a mismatched `Content-Range`, or writing an unsolicited partial response.

The reusable unit deliberately contains only the protocol decision logic. It performs no networking and no filesystem I/O.

## Core rules

Given the number of bytes already present locally plus the HTTP response status/header:

- existing partial + `206` + matching `Content-Range` start -> append;
- existing partial + `200` -> truncate/restart from zero;
- existing partial + mismatched/missing `Content-Range` -> reject;
- empty destination + `200` -> write fresh;
- empty destination + unsolicited `206` -> reject;
- other statuses -> reject body writes.

A separate helper captures the AERIS `416 Range Not Satisfiable` rule: an existing partial may be accepted as complete only when an independent integrity check already proves it matches the expected object.

## Use

```cpp
#include "http_resume_policy.hpp"

using namespace snippets::http_resume;

auto decision = decide_response_body(
    existing_bytes,
    http_status,
    content_range_header
);

if (decision.action == ResponseAction::append) {
    // seek to existing_bytes and append
} else if (decision.action == ResponseAction::restart_from_zero) {
    // truncate, seek to zero, then write response body
}
```

See `docs/specification.md`, `docs/architecture.md`, and `docs/limitations.md` for the exact contract.
