#include "game/session.hpp"
#include "url.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace game {
namespace {

void set_error(std::string* error, const std::string& message) {
    if (error) *error = message;
}

// Posts a JSON body and reports whether the API accepted it.
bool post_json(const std::string& base_url,
               const std::string& path,
               const json& body,
               std::string* error) {
    const auto parsed = detail::parse_url(base_url);
    httplib::Client client(parsed.host, parsed.port);
    client.set_connection_timeout(5, 0);
    client.set_read_timeout(10, 0);

    const auto res = client.Post(path.c_str(), body.dump(), "application/json");
    if (!res) {
        set_error(error, "Connection failed");
        return false;
    }
    if (res->status < 200 || res->status >= 300) {
        std::string detail = "HTTP " + std::to_string(res->status);
        try {
            const auto parsed_body = json::parse(res->body);
            if (parsed_body.contains("detail")) {
                const auto& d = parsed_body["detail"];
                detail = d.is_string() ? d.get<std::string>() : d.dump();
            }
        } catch (const json::exception&) {
            // keep the status-code message
        }
        set_error(error, detail);
        return false;
    }
    return true;
}

} // namespace

bool Session::submit_result(const std::string& base_url,
                            const MatchResultReport& result,
                            std::string* error) {
    if (result.match_id.empty()) {
        set_error(error, "match_id is required");
        return false;
    }

    json stats = json::object();
    if (!result.player_stats_json.empty()) {
        try {
            stats = json::parse(result.player_stats_json);
        } catch (const json::exception&) {
            set_error(error, "player_stats_json is not valid JSON");
            return false;
        }
    }

    const json body = {
        {"match_id", result.match_id},
        {"winner_team", result.winner_team},
        {"player_stats", stats},
        {"duration_seconds", result.duration_seconds},
    };

    return post_json(base_url, "/v1/session/" + result.match_id + "/result", body, error);
}

bool Session::heartbeat(const std::string& base_url,
                        const std::string& match_id,
                        const std::string& server_id,
                        int active_players,
                        std::string* error) {
    if (match_id.empty()) {
        set_error(error, "match_id is required");
        return false;
    }

    const json body = {
        {"match_id", match_id},
        {"server_id", server_id},
        {"active_players", active_players},
    };

    return post_json(base_url, "/v1/session/" + match_id + "/heartbeat", body, error);
}

} // namespace game
