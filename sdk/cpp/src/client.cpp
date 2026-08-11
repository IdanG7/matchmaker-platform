#include "game/client.hpp"
#include "transport.hpp"
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <memory>
#include <mutex>
#include <atomic>
#include <condition_variable>
#include <chrono>

using json = nlohmann::json;

namespace game {

namespace {

// --- Response parsing -----------------------------------------------------

// Pulls the API's error message out of a body, falling back to a generic one.
std::string error_detail(const std::string& body, const std::string& fallback) {
    try {
        const auto parsed = json::parse(body);
        if (parsed.contains("detail")) {
            const auto& detail = parsed["detail"];
            if (detail.is_string()) return detail.get<std::string>();
            return detail.dump();
        }
    } catch (const json::exception&) {
        // fall through
    }
    return fallback;
}

std::string get_string(const json& j, const char* key) {
    if (!j.contains(key) || j[key].is_null()) return {};
    const auto& v = j[key];
    return v.is_string() ? v.get<std::string>() : v.dump();
}

int get_int(const json& j, const char* key, int fallback = 0) {
    if (!j.contains(key) || !j[key].is_number_integer()) return fallback;
    return j[key].get<int>();
}

bool get_bool(const json& j, const char* key, bool fallback = false) {
    if (!j.contains(key) || !j[key].is_boolean()) return fallback;
    return j[key].get<bool>();
}

Party parse_party(const json& j) {
    Party party;
    party.id = get_string(j, "id");
    party.leader_id = get_string(j, "leader_id");
    party.region = get_string(j, "region");
    party.size = get_int(j, "size");
    party.max_size = get_int(j, "max_size");
    party.status = get_string(j, "status");
    party.queue_mode = get_string(j, "queue_mode");
    party.team_size = get_int(j, "team_size");

    // The API returns full member objects under "members".
    if (j.contains("members") && j["members"].is_array()) {
        for (const auto& m : j["members"]) {
            if (!m.is_object()) continue;
            PartyMember member;
            member.player_id = get_string(m, "player_id");
            member.username = get_string(m, "username");
            member.joined_at = get_string(m, "joined_at");
            member.ready = get_bool(m, "ready");
            member.role = get_string(m, "role");
            party.members.push_back(std::move(member));
        }
    }
    return party;
}

Profile parse_profile(const json& j) {
    Profile profile;
    // The profile endpoint names this "player_id"; "id" is accepted as a
    // fallback so a future rename does not silently empty the field again.
    profile.id = get_string(j, "player_id");
    if (profile.id.empty()) profile.id = get_string(j, "id");
    profile.username = get_string(j, "username");
    profile.email = get_string(j, "email");
    profile.region = get_string(j, "region");
    profile.mmr = get_int(j, "mmr");
    profile.party_id = get_string(j, "party_id");
    return profile;
}

ReadyCheck parse_ready_check(const json& j) {
    ReadyCheck rc;
    rc.party_id = get_string(j, "party_id");
    rc.ready_count = get_int(j, "ready_count");
    rc.total_count = get_int(j, "total_count");
    rc.all_ready = get_bool(j, "all_ready");
    if (j.contains("not_ready_players") && j["not_ready_players"].is_array()) {
        for (const auto& p : j["not_ready_players"]) {
            if (p.is_string()) rc.not_ready_players.push_back(p.get<std::string>());
        }
    }
    return rc;
}

MatchInfo parse_match_info(const json& j) {
    MatchInfo match;
    match.match_id = get_string(j, "match_id");
    match.server_endpoint = get_string(j, "server_endpoint");
    // The server names this field "server_token".
    match.server_token = get_string(j, "server_token");
    match.region = get_string(j, "region");
    match.mode = get_string(j, "mode");

    if (j.contains("teams") && j["teams"].is_array()) {
        for (const auto& team : j["teams"]) {
            if (!team.is_array()) continue;
            std::vector<std::string> members;
            for (const auto& m : team) {
                if (m.is_string()) members.push_back(m.get<std::string>());
            }
            match.teams.push_back(std::move(members));
        }
    }
    return match;
}

} // namespace

bool MatchInfo::split_endpoint(std::string& host, uint16_t& port) const {
    const size_t colon = server_endpoint.rfind(':');
    if (colon == std::string::npos || colon == 0 || colon + 1 >= server_endpoint.size()) {
        return false;
    }
    unsigned long parsed = 0;
    try {
        parsed = std::stoul(server_endpoint.substr(colon + 1));
    } catch (const std::exception&) {
        return false;
    }
    if (parsed == 0 || parsed > 65535) return false;

    host = server_endpoint.substr(0, colon);
    port = static_cast<uint16_t>(parsed);
    return true;
}

// --- Client ---------------------------------------------------------------

class Client::Impl {
public:
    std::string base_url;
    std::string token;
    std::string player_id;  // cached profile id, filled on first use

    MatchFoundCallback match_found_callback;
    LobbyUpdateCallback lobby_update_callback;
    EventCallback event_callback;
    std::mutex callback_mutex;

    std::unique_ptr<detail::WebSocket> ws_client;

    Impl(const std::string& url, const std::string& tok) : base_url(url), token(tok) {}

    detail::Headers auth_headers() const {
        return {{"Authorization", "Bearer " + token},
                {"Content-Type", "application/json"}};
    }

    // Single place where an HTTP call is made, checked, and parsed. Every
    // endpoint below goes through here so error handling stays consistent,
    // and the transport underneath differs between native and browser builds.
    json request(const char* method,
                 const std::string& path,
                 const std::string& body,
                 const std::string& what) {
        const auto res =
            detail::http_request(base_url, method, path, body, auth_headers());

        if (!res.transport_ok) {
            throw std::runtime_error(what + ": " + res.error + " (" + base_url + ")");
        }
        if (res.status < 200 || res.status >= 300) {
            throw std::runtime_error(
                what + ": " + error_detail(res.body, "HTTP " + std::to_string(res.status)));
        }
        if (res.body.empty()) return json::object();
        try {
            return json::parse(res.body);
        } catch (const json::exception&) {
            throw std::runtime_error(what + ": server returned malformed JSON");
        }
    }

    void handle_ws_event(const std::string& event, const json& data) {
        MatchFoundCallback on_match;
        LobbyUpdateCallback on_lobby;
        EventCallback on_event;
        {
            std::lock_guard<std::mutex> lock(callback_mutex);
            on_match = match_found_callback;
            on_lobby = lobby_update_callback;
            on_event = event_callback;
        }

        if (event == "match_found") {
            if (on_match) on_match(parse_match_info(data));
        } else if (on_lobby) {
            LobbyEvent ev;
            ev.party_id = get_string(data, "party_id");
            ev.player_id = get_string(data, "player_id");
            ev.username = get_string(data, "username");

            bool recognised = true;
            if (event == "member_joined") {
                ev.change = LobbyChange::MemberJoined;
            } else if (event == "member_left") {
                ev.change = LobbyChange::MemberLeft;
            } else if (event == "member_ready") {
                ev.change = LobbyChange::MemberReady;
                ev.ready = get_bool(data, "ready");
            } else if (event == "queue_entered") {
                ev.change = LobbyChange::QueueEntered;
                ev.mode = get_string(data, "mode");
                ev.team_size = get_int(data, "team_size");
            } else if (event == "queue_left") {
                ev.change = LobbyChange::QueueLeft;
            } else if (event == "party_updated") {
                ev.change = LobbyChange::PartyUpdated;
                if (data.contains("party") && data["party"].is_object()) {
                    ev.party = parse_party(data["party"]);
                }
            } else {
                recognised = false;
            }
            if (recognised) on_lobby(ev);
        }

        if (on_event) {
            Event e;
            e.name = event;
            e.data = data.dump();
            if (event == "match_found") {
                e.type = EventType::MatchFound;
            } else if (event == "session_started") {
                e.type = EventType::SessionStarted;
            } else if (event == "session_ended") {
                e.type = EventType::SessionEnded;
            } else if (event == "error") {
                e.type = EventType::Error;
            } else if (event == "presence" || event == "heartbeat") {
                e.type = EventType::PresenceHeartbeat;
            } else {
                e.type = EventType::LobbyUpdate;
            }
            on_event(e);
        }
    }
};

Client::Client(const std::string& base_url, const std::string& token)
    : impl_(std::make_unique<Impl>(base_url, token)) {}

Client::~Client() = default;

const std::string& Client::token() const {
    return impl_->token;
}

Profile Client::get_profile() {
    return parse_profile(impl_->request("GET", "/v1/profile/me", "", "Failed to get profile"));
}

void Client::update_profile(const Profile& profile) {
    json body = json::object();
    if (!profile.username.empty()) body["username"] = profile.username;
    if (!profile.region.empty()) body["region"] = profile.region;
    impl_->request("PATCH", "/v1/profile/me", body.dump(), "Failed to update profile");
}

Party Client::create_party() {
    return parse_party(impl_->request("POST", "/v1/party", "{}", "Failed to create party"));
}

Party Client::get_party(const std::string& party_id) {
    return parse_party(
        impl_->request("GET", "/v1/party/" + party_id, "", "Failed to get party"));
}

Party Client::join_party(const std::string& party_id) {
    return parse_party(
        impl_->request("POST", "/v1/party/" + party_id + "/join", "{}", "Failed to join party"));
}

void Client::leave_party(const std::string& party_id) {
    impl_->request("POST", "/v1/party/" + party_id + "/leave", "{}", "Failed to leave party");
}

ReadyCheck Client::toggle_ready(const std::string& party_id) {
    return parse_ready_check(impl_->request(
        "POST", "/v1/party/" + party_id + "/ready", "{}", "Failed to toggle ready"));
}

ReadyCheck Client::set_ready(const std::string& party_id, bool ready) {
    const Party party = get_party(party_id);

    // Work out our own membership. The profile id is stable for the session,
    // so it is fetched once and reused.
    if (impl_->player_id.empty()) {
        impl_->player_id = get_profile().id;
    }

    const PartyMember* self = nullptr;
    for (const auto& member : party.members) {
        if (member.player_id == impl_->player_id) {
            self = &member;
            break;
        }
    }
    if (!self) {
        throw std::runtime_error("Failed to set ready: not a member of party " + party_id);
    }

    if (self->ready == ready) {
        // Already in the requested state; report the tally without toggling.
        ReadyCheck rc;
        rc.party_id = party.id;
        rc.total_count = static_cast<int>(party.members.size());
        for (const auto& member : party.members) {
            if (member.ready) {
                ++rc.ready_count;
            } else {
                rc.not_ready_players.push_back(member.username);
            }
        }
        rc.all_ready = rc.total_count > 0 && rc.ready_count == rc.total_count;
        return rc;
    }

    return toggle_ready(party_id);
}

Party Client::enqueue(const std::string& party_id, const std::string& mode, int team_size) {
    const json body = {{"mode", mode}, {"team_size", team_size}};
    return parse_party(impl_->request(
        "POST", "/v1/party/" + party_id + "/queue", body.dump(), "Failed to enter queue"));
}

Party Client::cancel_queue(const std::string& party_id) {
    return parse_party(impl_->request(
        "POST", "/v1/party/" + party_id + "/unqueue", "{}", "Failed to leave queue"));
}

void Client::connect_ws(const std::string& party_id) {
    std::string ws_url = impl_->base_url;
    if (ws_url.rfind("http://", 0) == 0) {
        ws_url = "ws://" + ws_url.substr(7);
    } else if (ws_url.rfind("https://", 0) == 0) {
        ws_url = "wss://" + ws_url.substr(8);
    }
    while (!ws_url.empty() && ws_url.back() == '/') ws_url.pop_back();
    ws_url += "/v1/ws/party/" + party_id;

    // The token rides in the query string: browsers cannot set headers on a
    // WebSocket handshake, so this is the only option that works on both.
    ws_url += "?token=" + impl_->token;

    auto client = std::make_unique<detail::WebSocket>();
    client->set_message_handler([this](const std::string& frame) {
        json parsed;
        try {
            parsed = json::parse(frame);
        } catch (const json::exception&) {
            return; // ignore malformed frames
        }
        impl_->handle_ws_event(parsed.value("event", ""),
                               parsed.value("data", json::object()));
    });

    if (!client->connect(ws_url, std::chrono::seconds(5))) {
        throw std::runtime_error("Failed to open party WebSocket at " + ws_url);
    }
    impl_->ws_client = std::move(client);
}

void Client::disconnect_ws() {
    if (impl_->ws_client) {
        impl_->ws_client->disconnect();
        impl_->ws_client.reset();
    }
}

bool Client::is_ws_connected() const {
    return impl_->ws_client && impl_->ws_client->is_connected();
}

void Client::on_match_found(MatchFoundCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->callback_mutex);
    impl_->match_found_callback = std::move(callback);
}

void Client::on_lobby_update(LobbyUpdateCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->callback_mutex);
    impl_->lobby_update_callback = std::move(callback);
}

void Client::on_event(EventCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->callback_mutex);
    impl_->event_callback = std::move(callback);
}

} // namespace game
