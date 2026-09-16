# Specification

## Runtime

C++17 standard library only.

## API

The public header is `src/http_resume_policy.hpp` in namespace `snippets::http_resume`.

### `parse_content_range_start`

```cpp
std::optional<std::uint64_t> parse_content_range_start(std::string_view header) noexcept;
```

Accepted syntax begins with the exact prefix `bytes ` followed by one or more decimal digits and `-`.

Examples:

- `bytes 100-199/200` -> `100`;
- `bytes 0-99/*` -> `0`;
- `items 100-199/200` -> invalid;
- `bytes -199/200` -> invalid;
- decimal overflow beyond `uint64_t` -> invalid.

The function intentionally parses only the range start because that is the field needed to prove safe append alignment.

### `decide_response_body`

```cpp
ResponseDecision decide_response_body(
    std::uint64_t existing_partial_bytes,
    int http_status,
    std::string_view content_range
) noexcept;
```

Decision table:

| Existing bytes | Status | Header condition | Action |
|---:|---:|---|---|
| `>0` | `206` | start == existing bytes | `append` |
| `>0` | `206` | missing/invalid/mismatch | `reject` |
| `>0` | `200` | any | `restart_from_zero` |
| `>0` | other | any | `reject` |
| `0` | `200` | any | `write_fresh` |
| `0` | other, including `206` | any | `reject` |

`ResponseDecision::writable()` is true for all actions except `reject`.

### `accept_verified_partial_after_416`

```cpp
bool accept_verified_partial_after_416(
    int http_status,
    bool partial_matches_expected_identity
) noexcept;
```

Returns true only when `http_status == 416` and an independent integrity verifier has already confirmed the local partial matches the expected complete object.

## Invariants

- The policy never authorizes append after a `200` response.
- The policy never authorizes append when the `206` start differs from the local prefix length.
- An unsolicited `206` cannot become a fresh complete object through this API.
- The policy does not treat `416` as success without an independent identity check.
