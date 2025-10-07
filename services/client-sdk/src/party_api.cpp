#include "matchmaker/party_api.hpp"

namespace matchmaker {

PartyAPI::PartyAPI(std::shared_ptr<HTTPClient> http_client)
    : http_(std::move(http_client)) {
}

static PartyInfo parse_party(const json& data) {
    PartyInfo party;

    if (data.contains("party_id")) {
        party.party_id = data["party_id"].get<std::string>();
    } else if (data.contains("id")) {
        party.party_id = data["id"].get<std::string>();
    }

    party.leader_id = data.value("leader_id", "");
    party.region = data.value("region", "");
    party.status = data.value("status", "");
    party.size = data.value("size", 0);
    party.max_size = data.value("max_size", 0);
    party.created_at = data.value("created_at", "");

    if (data.contains("members") && data["members"].is_array()) {
        for (const auto& m : data["members"]) {
            PartyMember member;
            member.player_id = m.value("player_id", "");
            member.username = m.value("username", "");
            member.is_ready = m.value("ready", m.value("is_ready", false));
            // Some responses include is_leader; otherwise derive from leader_id
            member.is_leader = m.value("is_leader", false) ||
                               (!party.leader_id.empty() && member.player_id == party.leader_id);
            party.members.push_back(member);
        }
    }

    return party;
}

Result<PartyInfo> PartyAPI::create_party(int max_size) {
    json body = {
        {"max_size", max_size}
    };

    auto result = http_->post("/v1/party", body);

    if (!result) {
        return Result<PartyInfo>::Failure(result.error);
    }

    return Result<PartyInfo>::Success(parse_party(result.value));
}

Result<PartyInfo> PartyAPI::join_party(const std::string& party_id) {
    auto result = http_->post("/v1/party/" + party_id + "/join", json::object());

    if (!result) {
        return Result<PartyInfo>::Failure(result.error);
    }

    return Result<PartyInfo>::Success(parse_party(result.value));
}

Result<void> PartyAPI::leave_party(const std::string& party_id) {
    auto result = http_->post("/v1/party/" + party_id + "/leave", json::object());

    if (!result) {
        return Result<void>::Failure(result.error);
    }

    return Result<void>::Success();
}

Result<PartyInfo> PartyAPI::set_ready(const std::string& party_id, bool ready) {
    json body = {
        {"ready", ready}
    };

    auto result = http_->post("/v1/party/" + party_id + "/ready", body);

    if (!result) {
        return Result<PartyInfo>::Failure(result.error);
    }

    return Result<PartyInfo>::Success(parse_party(result.value));
}

Result<PartyInfo> PartyAPI::get_party(const std::string& party_id) {
    auto result = http_->get("/v1/party/" + party_id);

    if (!result) {
        return Result<PartyInfo>::Failure(result.error);
    }

    return Result<PartyInfo>::Success(parse_party(result.value));
}

Result<PartyInfo> PartyAPI::enter_queue(const std::string& party_id, const QueueRequest& request) {
    json body = {
        {"mode", request.mode},
        {"team_size", request.team_size}
    };

    auto result = http_->post("/v1/party/" + party_id + "/queue", body);

    if (!result) {
        return Result<PartyInfo>::Failure(result.error);
    }

    return Result<PartyInfo>::Success(parse_party(result.value));
}

Result<PartyInfo> PartyAPI::leave_queue(const std::string& party_id) {
    auto result = http_->post("/v1/party/" + party_id + "/unqueue", json::object());

    if (!result) {
        return Result<PartyInfo>::Failure(result.error);
    }

    return Result<PartyInfo>::Success(parse_party(result.value));
}

} // namespace matchmaker
