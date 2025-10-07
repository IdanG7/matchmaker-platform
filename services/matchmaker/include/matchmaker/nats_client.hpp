#pragma once

#include "queue_manager.hpp"
#include <string>
#include <functional>
#include <memory>

namespace matchmaker {

/**
 * NATS Client - Simplified wrapper for pub/sub messaging
 *
 * Phase 4: Interface-only (can be mocked for testing)
 * Future: Integrate actual nats.c library
 */
class NatsClient {
public:
    using QueueEventCallback = std::function<void(const QueueEntry&)>;
    using DequeueEventCallback = std::function<void(const std::string& party_id)>;

    virtual ~NatsClient() = default;

    // Subscribe to queue events
    virtual bool subscribe_queue_events(
        const std::string& subject,
        QueueEventCallback callback
    ) = 0;

    // Publish match found event
    virtual bool publish_match_found(const MatchResult& match) = 0;

    // Connection management
    virtual bool connect(const std::string& url) = 0;
    virtual void disconnect() = 0;
    virtual bool is_connected() const = 0;
};

/**
 * Mock NATS client for testing (no actual network connection)
 */
class MockNatsClient : public NatsClient {
public:
    bool subscribe_queue_events(
        const std::string& /*subject*/,
        QueueEventCallback callback
    ) override {
        queue_callback_ = callback;
        return true;
    }

    bool publish_match_found(const MatchResult& match) override {
        last_match_ = match;
        match_count_++;
        return true;
    }

    bool connect(const std::string& /*url*/) override {
        connected_ = true;
        return true;
    }

    void disconnect() override {
        connected_ = false;
    }

    bool is_connected() const override {
        return connected_;
    }

    // Test helpers
    void simulate_queue_event(const QueueEntry& entry) {
        if (queue_callback_) {
            queue_callback_(entry);
        }
    }

    const MatchResult& get_last_match() const { return last_match_; }
    size_t get_match_count() const { return match_count_; }

private:
    bool connected_ = false;
    QueueEventCallback queue_callback_;
    MatchResult last_match_;
    size_t match_count_ = 0;
};

/**
 * Factory function to create NATS client
 * Currently returns mock client, can be updated to return real client later
 */
inline std::unique_ptr<NatsClient> create_nats_client(bool use_mock = true) {
    if (use_mock) {
        return std::make_unique<MockNatsClient>();
    }
    // TODO: Return real NATS client when integrated
    return std::make_unique<MockNatsClient>();
}

} // namespace matchmaker
