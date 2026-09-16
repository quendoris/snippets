#include "../src/latest_preview_scheduler.hpp"

#include <cassert>
#include <string>

using snippets::latest_preview::Quality;
using snippets::latest_preview::RequestAction;
using snippets::latest_preview::Scheduler;

int main() {
    Scheduler<std::string> scheduler;

    const auto first = scheduler.request("preview-1", Quality::preview);
    assert(first.action == RequestAction::start);
    assert(first.launch.has_value());
    const auto first_generation = first.launch->generation;

    const auto queued = scheduler.request("preview-2", Quality::preview);
    assert(queued.action == RequestAction::queue_latest_preview);
    assert(!queued.launch.has_value());
    assert(scheduler.has_pending_preview());

    const auto replaced = scheduler.request("preview-3", Quality::preview);
    assert(replaced.action == RequestAction::queue_latest_preview);
    assert(!replaced.launch.has_value());

    const auto completed = scheduler.complete(first_generation);
    assert(completed.accepted);
    assert(completed.next.has_value());
    assert(completed.next->request == "preview-3");
    assert(completed.next->generation != first_generation);
    const auto latest_generation = completed.next->generation;

    const auto verified = scheduler.request("verified", Quality::verified);
    assert(verified.action == RequestAction::preempt_and_start);
    assert(verified.launch.has_value());
    assert(verified.launch->quality == Quality::verified);
    const auto verified_generation = verified.launch->generation;
    assert(verified_generation != latest_generation);
    assert(!scheduler.has_pending_preview());

    const auto stale = scheduler.complete(latest_generation);
    assert(!stale.accepted);
    assert(!stale.next.has_value());

    const auto interactive = scheduler.request("preview-after-verified", Quality::preview);
    assert(interactive.action == RequestAction::preempt_and_start);
    assert(interactive.launch.has_value());
    assert(interactive.launch->quality == Quality::preview);
    const auto interactive_generation = interactive.launch->generation;

    const auto final = scheduler.complete(interactive_generation);
    assert(final.accepted);
    assert(!final.next.has_value());
    assert(!scheduler.running());

    const auto idle_verified = scheduler.request("verified-idle", Quality::verified);
    assert(idle_verified.action == RequestAction::start);
    assert(idle_verified.launch.has_value());
    const auto canceled_generation = idle_verified.launch->generation;
    scheduler.cancel();
    assert(!scheduler.running());
    assert(!scheduler.has_pending_preview());
    assert(scheduler.generation() != canceled_generation);
    const auto after_cancel = scheduler.complete(canceled_generation);
    assert(!after_cancel.accepted);

    return 0;
}
