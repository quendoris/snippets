# Limitations

## Policy only

This snippet does not perform HTTP requests, file writes, hashing, retries, timeout handling, redirect validation, progress reporting, cancellation, or atomic publication. Those responsibilities stay with the consuming downloader.

## `Content-Range` parsing is intentionally narrow

Only the numeric range start is parsed. The end offset and complete-object size are not validated. A caller that needs stronger representation validation must add those checks separately.

## Representation identity is external

Safe offset alignment is not the same as safe object identity. If the remote object can change between requests, use a validator such as `If-Range` with a strong ETag or otherwise bind acquisition to an immutable object identity.

The AERIS Natural Earth source that motivated this snippet is commit-pinned and additionally SHA-256 verified after download. Those guarantees are not supplied by this policy itself.

## `416` requires independent verification

The `416` helper deliberately accepts only a boolean result from another verifier. It does not infer completeness from local size alone.

## No HTTP library assumptions

The snippet uses status/header values already obtained by the caller. It does not normalize library-specific header encodings or HTTP/2/HTTP/3 behavior.
