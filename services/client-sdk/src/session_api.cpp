#include "matchmaker/session_api.hpp"

namespace matchmaker {

SessionAPI::SessionAPI(std::shared_ptr<HTTPClient> http_client)
    : http_(std::move(http_client)) {
}

Result<SessionInfo> SessionAPI::get_session(const std::string& match_id) {
    auto result = http_->get("/v1/session/" + match_id);

    if (!result) {
        return Result<SessionInfo>::Failure(result.error);
    }

    SessionInfo session;
    session.match_id = result.value["match_id"];
    session.status = result.value["status"];
    session.server_endpoint = result.value.value("server_endpoint", "");
    session.server_token = result.value.value("server_token", "");
    session.region = result.value["region"];
    session.mode = result.value["mode"];

    if (result.value.contains("player_ids")) {
        for (const auto& id : result.value["player_ids"]) {
            session.player_ids.push_back(id);
        }
    }

    session.started_at = result.value.value("started_at", "");

    return Result<SessionInfo>::Success(session);
}

Result<void> SessionAPI::send_heartbeat(const std::string& match_id) {
    auto result = http_->post("/v1/session/" + match_id + "/heartbeat", json::object());

    if (!result) {
        return Result<void>::Failure(result.error);
    }

    return Result<void>::Success();
}

Result<void> SessionAPI::submit_result(const MatchResult& result_data) {
    json body = {
        {"match_id", result_data.match_id},
        {"winner_team", result_data.winner_team},
        {"player_stats", result_data.player_stats},
        {"duration_seconds", result_data.duration_seconds}
    };

    auto result = http_->post(
        "/v1/session/" + result_data.match_id + "/result",
        body
    );

    if (!result) {
        return Result<void>::Failure(result.error);
    }

    return Result<void>::Success();
}

} // namespace matchmaker
