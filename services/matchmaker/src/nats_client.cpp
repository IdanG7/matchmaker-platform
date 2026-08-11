#include "matchmaker/nats_client.hpp"

#include <nats.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <chrono>
#include <mutex>

using json = nlohmann::json;

namespace matchmaker {
namespace {

// The API publishes ISO-8601 timestamps; the queue only needs a monotonic
// arrival time, so entries are stamped on receipt rather than parsed.
QueueEntry parse_queue_enter(const json& j) {
    QueueEntry entry;
    entry.party_id = j.value("party_id", "");
    entry.region = j.value("region", "");
    entry.mode = j.value("mode", "");
    entry.team_size = j.value("team_size", 0);
    entry.party_size = j.value("party_size", 0);
    entry.avg_mmr = j.value("avg_mmr", 0);
    entry.enqueued_at = std::chrono::system_clock::now();

    if (j.contains("player_ids") && j["player_ids"].is_array()) {
        for (const auto& id : j["player_ids"]) {
            if (id.is_string()) entry.player_ids.push_back(id.get<std::string>());
        }
    }
    return entry;
}

json serialise_match(const MatchResult& match) {
    return json{
        {"match_id", match.match_id},
        {"region", match.region},
        {"mode", match.mode},
        {"team_size", match.team_size},
        {"teams", match.teams},
        {"party_ids", match.party_ids},
        {"avg_mmr", match.avg_mmr},
        {"mmr_variance", match.mmr_variance},
        {"quality_score", match.quality_score},
    };
}

class RealNatsClient : public NatsClient {
public:
    ~RealNatsClient() override { disconnect(); }

    bool connect(const std::string& url) override {
        natsStatus status = natsConnection_ConnectTo(&conn_, url.c_str());
        if (status != NATS_OK) {
            spdlog::error("NATS connect to {} failed: {}", url, natsStatus_GetText(status));
            conn_ = nullptr;
            return false;
        }
        spdlog::info("Connected to NATS at {}", url);
        return true;
    }

    void disconnect() override {
        if (sub_) {
            natsSubscription_Destroy(sub_);
            sub_ = nullptr;
        }
        if (conn_) {
            natsConnection_Destroy(conn_);
            conn_ = nullptr;
        }
    }

    bool is_connected() const override {
        return conn_ != nullptr && natsConnection_Status(conn_) == NATS_CONN_STATUS_CONNECTED;
    }

    bool subscribe_queue_events(const std::string& subject,
                                QueueEnterCallback on_enter,
                                QueueLeaveCallback on_leave) override {
        if (!conn_) {
            spdlog::error("Cannot subscribe before connecting");
            return false;
        }
        on_enter_ = std::move(on_enter);
        on_leave_ = std::move(on_leave);

        const natsStatus status =
            natsConnection_Subscribe(&sub_, conn_, subject.c_str(), &RealNatsClient::onMessage, this);
        if (status != NATS_OK) {
            spdlog::error("NATS subscribe to {} failed: {}", subject, natsStatus_GetText(status));
            return false;
        }
        spdlog::info("Subscribed to {}", subject);
        return true;
    }

    bool publish_match_found(const MatchResult& match) override {
        if (!conn_) return false;

        const std::string payload = serialise_match(match).dump();
        const natsStatus status =
            natsConnection_PublishString(conn_, "match.found", payload.c_str());
        if (status != NATS_OK) {
            spdlog::error("Publishing match.found failed: {}", natsStatus_GetText(status));
            return false;
        }
        // Without a flush a match can sit in the buffer while the process is
        // shutting down, which loses the event the API is waiting on.
        natsConnection_Flush(conn_);
        return true;
    }

private:
    // Called on a NATS library thread.
    static void onMessage(natsConnection*, natsSubscription*, natsMsg* msg, void* closure) {
        auto* self = static_cast<RealNatsClient*>(closure);
        const std::string payload(natsMsg_GetData(msg),
                                  static_cast<size_t>(natsMsg_GetDataLength(msg)));
        natsMsg_Destroy(msg);

        json parsed;
        try {
            parsed = json::parse(payload);
        } catch (const json::exception& e) {
            spdlog::warn("Ignoring malformed queue event: {}", e.what());
            return;
        }

        const std::string event_type = parsed.value("event_type", "");
        try {
            if (event_type == "queue_enter") {
                if (self->on_enter_) self->on_enter_(parse_queue_enter(parsed));
            } else if (event_type == "queue_leave") {
                if (self->on_leave_) self->on_leave_(parsed.value("party_id", ""));
            } else {
                spdlog::debug("Ignoring queue event of type '{}'", event_type);
            }
        } catch (const std::exception& e) {
            spdlog::warn("Failed to handle queue event: {}", e.what());
        }
    }

    natsConnection* conn_ = nullptr;
    natsSubscription* sub_ = nullptr;
    QueueEnterCallback on_enter_;
    QueueLeaveCallback on_leave_;
};

} // namespace

std::unique_ptr<NatsClient> create_nats_client(bool use_mock) {
    if (use_mock) {
        return std::make_unique<MockNatsClient>();
    }
    return std::make_unique<RealNatsClient>();
}

} // namespace matchmaker
