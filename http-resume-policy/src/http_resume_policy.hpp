#pragma once

#include <cstdint>
#include <limits>
#include <optional>
#include <string_view>

namespace snippets::http_resume {

enum class ResponseAction {
    reject,
    write_fresh,
    append,
    restart_from_zero,
};

struct ResponseDecision final {
    ResponseAction action{ResponseAction::reject};

    [[nodiscard]] constexpr bool writable() const noexcept {
        return action != ResponseAction::reject;
    }
};

[[nodiscard]] inline std::optional<std::uint64_t> parse_content_range_start(
    const std::string_view header
) noexcept {
    constexpr std::string_view prefix{"bytes "};
    if (!header.starts_with(prefix)) return std::nullopt;

    const std::size_t first = prefix.size();
    const std::size_t dash = header.find('-', first);
    if (dash == std::string_view::npos || dash == first) return std::nullopt;

    std::uint64_t value = 0U;
    for (std::size_t index = first; index < dash; ++index) {
        const char ch = header[index];
        if (ch < '0' || ch > '9') return std::nullopt;
        const std::uint64_t digit = static_cast<std::uint64_t>(ch - '0');
        if (value > (std::numeric_limits<std::uint64_t>::max() - digit) / 10U) {
            return std::nullopt;
        }
        value = value * 10U + digit;
    }
    return value;
}

[[nodiscard]] inline ResponseDecision decide_response_body(
    const std::uint64_t existing_partial_bytes,
    const int http_status,
    const std::string_view content_range
) noexcept {
    if (existing_partial_bytes > 0U) {
        if (http_status == 206) {
            const std::optional<std::uint64_t> start =
                parse_content_range_start(content_range);
            if (start && *start == existing_partial_bytes) {
                return {ResponseAction::append};
            }
            return {ResponseAction::reject};
        }

        if (http_status == 200) {
            // A server may ignore Range and return the complete representation.
            // The safe response is to truncate the old prefix before writing.
            return {ResponseAction::restart_from_zero};
        }

        return {ResponseAction::reject};
    }

    if (http_status == 200) {
        return {ResponseAction::write_fresh};
    }

    // In particular, an unsolicited 206 must not become a new local file.
    return {ResponseAction::reject};
}

[[nodiscard]] inline constexpr bool accept_verified_partial_after_416(
    const int http_status,
    const bool partial_matches_expected_identity
) noexcept {
    return http_status == 416 && partial_matches_expected_identity;
}

}  // namespace snippets::http_resume
