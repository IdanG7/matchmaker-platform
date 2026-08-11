#pragma once

#include "queue_manager.hpp"
#include <string>
#include <functional>
#include <memory>

namespace matchmaker {

/**
 * NATS client for the matchmaker service.
 *
 * Inbound:  matchmaker.queue.{mode}.{region}, carrying queue_enter and
 *           queue_leave events published by the API.
 * Outbound: match.found, consumed by the API to create the match record and
 *           allocate a game server.
 */
class NatsClient {
public:
    using QueueEnterCallback = std::function<void(const QueueEntry&)>;
    using QueueLeaveCallback = std::function<void(const std::string& party_id)>;

    virtual ~NatsClient() = default;

    // Subscribes to queue events. The subject is a NATS pattern; use
    // "matchmaker.queue.>" to catch every mode and region, since '*' matches
    // only one token and the subject carries two after the prefix.
    virtual bool subscribe_queue_events(const std::string& subject,
                                        QueueEnterCallback on_enter,
                                        QueueLeaveCallback on_leave) = 0;

    virtual bool publish_match_found(const MatchResult& match) = 0;

    virtual bool connect(const std::string& url) = 0;
    virtual void disconnect() = 0;
    virtual bool is_connected() const = 0;
};

/**
 * In-memory client for tests: no sockets, events are driven by hand.
 */
class MockNatsClient : public NatsClient {
public:
    bool subscribe_queue_events(const std::string& /*subject*/,
                                QueueEnterCallback on_enter,
                                QueueLeaveCallback on_leave) override {
        on_enter_ = std::move(on_enter);
        on_leave_ = std::move(on_leave);
        return true;
    }

    bool publish_match_found(const MatchResult& match) override {
        last_match_ = match;
        matches_.push_back(match);
        return true;
    }

    bool connect(const std::string& /*url*/) override {
        connected_ = true;
        return true;
    }

    void disconnect() override { connected_ = false; }
    bool is_connected() const override { return connected_; }

    // Test helpers
    void simulate_queue_enter(const QueueEntry& entry) {
        if (on_enter_) on_enter_(entry);
    }
    void simulate_queue_leave(const std::string& party_id) {
        if (on_leave_) on_leave_(party_id);
    }

    const MatchResult& get_last_match() const { return last_match_; }
    size_t get_match_count() const { return matches_.size(); }
    const std::vector<MatchResult>& get_matches() const { return matches_; }

private:
    bool connected_ = false;
    QueueEnterCallback on_enter_;
    QueueLeaveCallback on_leave_;
    MatchResult last_match_;
    std::vector<MatchResult> matches_;
};

// Creates a client backed by a real NATS connection, or the in-memory mock.
std::unique_ptr<NatsClient> create_nats_client(bool use_mock = false);

} // namespace matchmaker
