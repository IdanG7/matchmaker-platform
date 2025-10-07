#include "matchmaker/party_api.hpp"

namespace matchmaker {

PartyAPI::PartyAPI(std::shared_ptr<HTTPClient> http_client)
    : http_(std::move(http_client)) {
}

static PartyInfo parse_party(const json& data) {
    PartyInfo party;
    party.party_id = data["party_id"];
    party.leader_id = data["leader_id"];
    party.region = data["region"];
    party.status = data["status"];
    party.size = data["size"];
    party.max_size = data["max_size"];
    party.created_at = data["created_at"];

    if (data.contains("members")) {
        for (const auto& m : data["members"]) {
            PartyMember member;
            member.player_id = m["player_id"];
            member.username = m["username"];
            member.is_leader = m["is_leader"];
            member.is_ready = m["is_ready"];
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

Result<void> PartyAPI::enter_queue(const QueueRequest& request) {
    json body = {
        {"mode", request.mode},
        {"team_size", request.team_size}
    };

    auto result = http_->post("/v1/party/queue", body);

    if (!result) {
        return Result<void>::Failure(result.error);
    }

    return Result<void>::Success();
}

Result<void> PartyAPI::leave_queue() {
    auto result = http_->del("/v1/party/queue");

    if (!result) {
        return Result<void>::Failure(result.error);
    }

    return Result<void>::Success();
}

} // namespace matchmaker
