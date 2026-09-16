# Architecture

## Origin

The policy was extracted from AERIS Desktop's `natural_earth_acquisition.cpp`. In that code, a Qt network request may begin with a local `.part` prefix and a `Range: bytes=<size>-` request. The downloader must decide whether the response body is safe to append, must replace the old prefix, or must not be written at all.

## Boundary

The snippet owns only this transition:

```text
local partial size
      +
HTTP status
      +
Content-Range
      ↓
write policy
```

It does not own sockets, redirects, retries, hashing, file publication, persistence, progress reporting, or cancellation.

Keeping the protocol decision pure makes the most corruption-sensitive part easy to unit-test without a network server.

## Why `200` after Range means restart

Some servers ignore Range and return the complete representation with `200 OK`. Appending that response to an existing prefix would duplicate bytes and corrupt the local object. The safe action is therefore `restart_from_zero`.

## Why `206` requires an exact start

A resumed `206 Partial Content` is writable only when the parsed `Content-Range` begins at exactly the number of bytes already present locally. Any other start would create a gap or overlap.

## Why unsolicited `206` is rejected

When there is no local prefix, the caller asked for the complete representation. An unsolicited `206` does not prove that the body starts at zero or represents the complete object, so the policy rejects it instead of silently materializing a partial file.

## `416` handling

AERIS observed one useful case: a `.part` may already contain the complete immutable object, while a subsequent Range request receives `416 Range Not Satisfiable`. The snippet therefore exposes a helper that accepts this situation only after a separate integrity verifier says the partial already matches the expected identity.
