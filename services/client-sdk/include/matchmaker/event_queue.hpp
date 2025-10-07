#pragma once

#include "types.hpp"
#include <queue>
#include <mutex>
#include <condition_variable>
#include <optional>

namespace matchmaker {

/**
 * Thread-safe event queue for delivering WebSocket events to the main thread.
 * Supports both polling and callback-based event handling.
 */
class EventQueue {
public:
    EventQueue() = default;
    ~EventQueue() = default;

    // Add event to queue (called from WebSocket thread)
    void push(Event event);

    // Poll for events (non-blocking)
    std::optional<Event> poll();

    // Wait for next event (blocking)
    Event wait();

    // Wait for next event with timeout (blocking)
    std::optional<Event> wait_for(std::chrono::milliseconds timeout);

    // Register callback for specific event type
    void on(EventType type, EventCallback callback);

    // Clear all pending events
    void clear();

    // Get number of pending events
    size_t size() const;

private:
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<Event> queue_;
    std::unordered_map<EventType, std::vector<EventCallback>> callbacks_;

    void dispatch_callbacks(const Event& event);
};

} // namespace matchmaker
