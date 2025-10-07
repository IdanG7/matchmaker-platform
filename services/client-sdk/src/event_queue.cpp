#include "matchmaker/event_queue.hpp"

namespace matchmaker {

void EventQueue::push(Event event) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(std::move(event));
    }
    cv_.notify_one();
}

std::optional<Event> EventQueue::poll() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (queue_.empty()) {
        return std::nullopt;
    }

    Event event = std::move(queue_.front());
    queue_.pop();

    // Dispatch to callbacks
    dispatch_callbacks(event);

    return event;
}

Event EventQueue::wait() {
    std::unique_lock<std::mutex> lock(mutex_);

    cv_.wait(lock, [this] { return !queue_.empty(); });

    Event event = std::move(queue_.front());
    queue_.pop();

    // Dispatch to callbacks
    dispatch_callbacks(event);

    return event;
}

std::optional<Event> EventQueue::wait_for(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(mutex_);

    if (!cv_.wait_for(lock, timeout, [this] { return !queue_.empty(); })) {
        return std::nullopt;  // Timeout
    }

    Event event = std::move(queue_.front());
    queue_.pop();

    // Dispatch to callbacks
    dispatch_callbacks(event);

    return event;
}

void EventQueue::on(EventType type, EventCallback callback) {
    std::lock_guard<std::mutex> lock(mutex_);
    callbacks_[type].push_back(std::move(callback));
}

void EventQueue::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    while (!queue_.empty()) {
        queue_.pop();
    }
}

size_t EventQueue::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.size();
}

void EventQueue::dispatch_callbacks(const Event& event) {
    auto it = callbacks_.find(event.type);
    if (it != callbacks_.end()) {
        for (const auto& callback : it->second) {
            callback(event);
        }
    }
}

} // namespace matchmaker
