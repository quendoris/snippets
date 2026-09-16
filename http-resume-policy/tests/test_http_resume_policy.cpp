#include "../src/http_resume_policy.hpp"

#include <cassert>
#include <cstdint>
#include <limits>
#include <string>

using snippets::http_resume::ResponseAction;
using snippets::http_resume::accept_verified_partial_after_416;
using snippets::http_resume::decide_response_body;
using snippets::http_resume::parse_content_range_start;

int main() {
    {
        const auto start = parse_content_range_start("bytes 123-456/789");
        assert(start.has_value());
        assert(*start == 123U);
    }
    assert(!parse_content_range_start("items 123-456/789").has_value());
    assert(!parse_content_range_start("bytes -456/789").has_value());
    assert(!parse_content_range_start("bytes 12x-456/789").has_value());

    {
        const std::string overflow =
            "bytes " + std::to_string(std::numeric_limits<std::uint64_t>::max()) +
            "0-1/2";
        assert(!parse_content_range_start(overflow).has_value());
    }

    assert(
        decide_response_body(100U, 206, "bytes 100-199/200").action ==
        ResponseAction::append
    );
    assert(
        decide_response_body(100U, 206, "bytes 99-199/200").action ==
        ResponseAction::reject
    );
    assert(
        decide_response_body(100U, 206, "").action ==
        ResponseAction::reject
    );
    assert(
        decide_response_body(100U, 200, "").action ==
        ResponseAction::restart_from_zero
    );
    assert(
        decide_response_body(0U, 200, "").action ==
        ResponseAction::write_fresh
    );
    assert(
        decide_response_body(0U, 206, "bytes 0-99/100").action ==
        ResponseAction::reject
    );
    assert(
        decide_response_body(100U, 500, "").action ==
        ResponseAction::reject
    );

    assert(accept_verified_partial_after_416(416, true));
    assert(!accept_verified_partial_after_416(416, false));
    assert(!accept_verified_partial_after_416(200, true));

    return 0;
}
