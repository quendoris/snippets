#pragma once

#include <cstdint>
#include <optional>
#include <utility>

namespace snippets::latest_preview {

enum class Quality { preview, verified };
enum class RequestAction { start, queue_latest_preview, preempt_and_start };

template <typename Request>
struct Launch final {
    std::uint64_t generation{0U};
    Quality quality{Quality::preview};
    Request request;
};

template <typename Request>
struct RequestDecision final {
    RequestAction action{RequestAction::start};
    std::optional<Launch<Request>> launch;
};

template <typename Request>
struct CompletionDecision final {
    bool accepted{false};
    std::optional<Launch<Request>> next;
};

template <typename Request>
class Scheduler final {
public:
    [[nodiscard]] RequestDecision<Request> request(Request value, Quality quality) {
        if (quality == Quality::preview && running_) {
            if (active_quality_ == Quality::preview) {
                pending_preview_ = std::move(value);
                return {RequestAction::queue_latest_preview, std::nullopt};
            }
            invalidate_running();
            return {RequestAction::preempt_and_start, start(std::move(value), quality)};
        }

        if (quality == Quality::verified) {
            pending_preview_.reset();
            if (running_) {
                invalidate_running();
                return {RequestAction::preempt_and_start, start(std::move(value), quality)};
            }
        }

        return {RequestAction::start, start(std::move(value), quality)};
    }

    [[nodiscard]] CompletionDecision<Request> complete(std::uint64_t generation) {
        if (!running_ || generation != generation_) return {false, std::nullopt};

        running_ = false;
        if (active_quality_ == Quality::preview && pending_preview_) {
            Request next = std::move(*pending_preview_);
            pending_preview_.reset();
            return {true, start(std::move(next), Quality::preview)};
        }

        pending_preview_.reset();
        return {true, std::nullopt};
    }

    void cancel() noexcept {
        pending_preview_.reset();
        invalidate_running();
    }

    [[nodiscard]] bool running() const noexcept { return running_; }
    [[nodiscard]] bool has_pending_preview() const noexcept { return pending_preview_.has_value(); }
    [[nodiscard]] std::uint64_t generation() const noexcept { return generation_; }

private:
    [[nodiscard]] Launch<Request> start(Request value, Quality quality) {
        ++generation_;
        running_ = true;
        active_quality_ = quality;
        return {generation_, quality, std::move(value)};
    }

    void invalidate_running() noexcept {
        ++generation_;
        running_ = false;
    }

    bool running_{false};
    Quality active_quality_{Quality::preview};
    std::optional<Request> pending_preview_;
    std::uint64_t generation_{0U};
};

}  // namespace snippets::latest_preview
