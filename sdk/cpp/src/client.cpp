#include "game/client.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <ixwebsocket/IXWebSocket.h>
#include <stdexcept>
#include <memory>
#include <mutex>

using json = nlohmann::json;

namespace game {

// Forward declaration of WebSocket wrapper
namespace {
    class WebSocketWrapper {
    public:
        WebSocketWrapper(const std::string& ws_url, const std::string& token)
            : connected_(false) {

            ws_.setUrl(ws_url + "?token=" + token);

            ws_.setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
                this->onMessage(msg);
            });
        }

        ~WebSocketWrapper() {
            disconnect();
        }

        void connect() {
            ws_.start();
            // Wait for connection
            for (int i = 0; i < 50; i++) {
                if (connected_) break;
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
        }

        void disconnect() {
            ws_.stop();
            connected_ = false;
        }

        bool is_connected() const {
            return connected_;
        }

        void set_event_callback(std::function<void(const std::string&, const json&)> callback) {
            std::lock_guard<std::mutex> lock(callback_mutex_);
            event_callback_ = callback;
        }

    private:
        void onMessage(const ix::WebSocketMessagePtr& msg) {
            if (msg->type == ix::WebSocketMessageType::Open) {
                connected_ = true;
            } else if (msg->type == ix::WebSocketMessageType::Close) {
                connected_ = false;
            } else if (msg->type == ix::WebSocketMessageType::Message) {
                try {
                    auto data = json::parse(msg->str);
                    std::string event = data.value("event", "unknown");
                    json event_data = data.value("data", json::object());

                    std::lock_guard<std::mutex> lock(callback_mutex_);
                    if (event_callback_) {
                        event_callback_(event, event_data);
                    }
                } catch (const std::exception&) {
                    // Ignore parse errors
                }
            } else if (msg->type == ix::WebSocketMessageType::Error) {
                connected_ = false;
            }
        }

        ix::WebSocket ws_;
        bool connected_;
        std::function<void(const std::string&, const json&)> event_callback_;
        std::mutex callback_mutex_;
    };
}

namespace {
    // Helper to parse URL into host and port
    struct ParsedURL {
        std::string scheme;
        std::string host;
        int port;
    };

    ParsedURL parse_url(const std::string& url) {
        ParsedURL result;
        size_t scheme_end = url.find("://");
        if (scheme_end != std::string::npos) {
            result.scheme = url.substr(0, scheme_end);
            size_t host_start = scheme_end + 3;
            size_t port_start = url.find(":", host_start);
            if (port_start != std::string::npos) {
                result.host = url.substr(host_start, port_start - host_start);
                result.port = std::stoi(url.substr(port_start + 1));
            } else {
                result.host = url.substr(host_start);
                result.port = (result.scheme == "https") ? 443 : 80;
            }
        } else {
            result.scheme = "http";
            result.host = "localhost";
            result.port = 8080;
        }
        return result;
    }
}

class Client::Impl {
public:
    std::string base_url;
    std::string token;
    ParsedURL parsed_url;
    MatchFoundCallback match_found_callback;
    LobbyUpdateCallback lobby_update_callback;
    EventCallback event_callback;
    std::unique_ptr<WebSocketWrapper> ws_client;

    Impl(const std::string& url, const std::string& tok)
        : base_url(url), token(tok), parsed_url(parse_url(url)) {}

    httplib::Headers get_auth_headers() const {
        return {
            {"Authorization", "Bearer " + token},
            {"Content-Type", "application/json"}
        };
    }

    void handle_ws_event(const std::string& event, const json& data) {
        // Dispatch to appropriate callback
        if (event == "match_found" && match_found_callback) {
            MatchInfo match;
            match.match_id = data.value("match_id", "");
            match.server_endpoint = data.value("server_endpoint", "");
            match.token = data.value("token", "");

            if (data.contains("teams") && data["teams"].is_array()) {
                for (const auto& team : data["teams"]) {
                    std::vector<std::string> team_members;
                    if (team.is_array()) {
                        for (const auto& member : team) {
                            team_members.push_back(member.get<std::string>());
                        }
                    }
                    match.teams.push_back(team_members);
                }
            }

            match_found_callback(match);
        } else if ((event == "member_joined" || event == "member_left" ||
                    event == "member_ready" || event == "party_updated") &&
                   lobby_update_callback) {
            Party party;
            party.id = data.value("party_id", "");
            party.leader_id = data.value("leader_id", "");
            party.status = data.value("status", "");

            if (data.contains("member_ids") && data["member_ids"].is_array()) {
                for (const auto& member : data["member_ids"]) {
                    party.member_ids.push_back(member.get<std::string>());
                }
            }

            lobby_update_callback(party);
        }

        // Always call general event callback if set
        if (event_callback) {
            Event e;
            e.type = EventType::LobbyUpdate; // Default, could be improved
            if (event == "match_found") e.type = EventType::MatchFound;
            e.data = data.dump();
            event_callback(e);
        }
    }
};

Client::Client(const std::string& base_url, const std::string& token)
    : impl_(std::make_unique<Impl>(base_url, token)) {}

Client::~Client() = default;

Profile Client::get_profile() {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    auto res = client.Get("/v1/profile/me", impl_->get_auth_headers());

    if (!res) {
        throw std::runtime_error("Failed to connect to server");
    }

    if (res->status == 200) {
        auto data = json::parse(res->body);
        return Profile{
            data.value("id", ""),
            data.value("username", ""),
            data.value("email", ""),
            data.value("region", ""),
            data.value("mmr", 0)
        };
    } else {
        auto error = json::parse(res->body);
        throw std::runtime_error(error.value("detail", "Failed to get profile"));
    }
}

void Client::update_profile(const Profile& profile) {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    json body;
    if (!profile.username.empty()) body["username"] = profile.username;
    if (!profile.region.empty()) body["region"] = profile.region;

    auto res = client.Patch("/v1/profile/me",
                           impl_->get_auth_headers(),
                           body.dump(),
                           "application/json");

    if (!res || res->status != 200) {
        throw std::runtime_error("Failed to update profile");
    }
}

Party Client::create_party() {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    auto res = client.Post("/v1/party",
                          impl_->get_auth_headers(),
                          "{}",
                          "application/json");

    if (!res) {
        throw std::runtime_error("Failed to connect to server");
    }

    if (res->status == 200 || res->status == 201) {
        auto data = json::parse(res->body);
        Party party;
        party.id = data.value("id", "");
        party.leader_id = data.value("leader_id", "");
        party.status = data.value("status", "");

        if (data.contains("member_ids") && data["member_ids"].is_array()) {
            for (const auto& member : data["member_ids"]) {
                party.member_ids.push_back(member.get<std::string>());
            }
        }

        return party;
    } else {
        auto error = json::parse(res->body);
        throw std::runtime_error(error.value("detail", "Failed to create party"));
    }
}

void Client::join_party(const std::string& party_id) {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    std::string path = "/v1/party/" + party_id + "/join";
    auto res = client.Post(path,
                          impl_->get_auth_headers(),
                          "{}",
                          "application/json");

    if (!res || res->status != 200) {
        auto error = res ? json::parse(res->body) : json::object();
        throw std::runtime_error(error.value("detail", "Failed to join party"));
    }
}

void Client::leave_party(const std::string& party_id) {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    std::string path = "/v1/party/" + party_id + "/leave";
    auto res = client.Delete(path, impl_->get_auth_headers());

    if (!res || res->status != 200) {
        throw std::runtime_error("Failed to leave party");
    }
}

void Client::ready() {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    // Note: This endpoint may need a party_id parameter
    // For now, we'll assume the backend tracks the player's current party
    auto res = client.Post("/v1/party/ready",
                          impl_->get_auth_headers(),
                          "{}",
                          "application/json");

    if (!res || res->status != 200) {
        throw std::runtime_error("Failed to set ready status");
    }
}

void Client::enqueue(const std::string& party_id, const std::string& mode, int team_size) {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    json body = {
        {"party_id", party_id},
        {"mode", mode},
        {"team_size", team_size}
    };

    auto res = client.Post("/v1/party/queue",
                          impl_->get_auth_headers(),
                          body.dump(),
                          "application/json");

    if (!res || res->status != 200) {
        auto error = res ? json::parse(res->body) : json::object();
        throw std::runtime_error(error.value("detail", "Failed to enter queue"));
    }
}

void Client::cancel_queue(const std::string& party_id) {
    httplib::Client client(impl_->parsed_url.host, impl_->parsed_url.port);
    client.set_connection_timeout(5, 0);

    std::string path = "/v1/party/queue?party_id=" + party_id;
    auto res = client.Delete(path, impl_->get_auth_headers());

    if (!res || res->status != 200) {
        throw std::runtime_error("Failed to leave queue");
    }
}

void Client::connect_ws(const std::string& party_id) {
    // Build WebSocket URL
    std::string ws_url = impl_->base_url;

    // Convert http:// to ws://
    if (ws_url.find("http://") == 0) {
        ws_url = "ws://" + ws_url.substr(7);
    } else if (ws_url.find("https://") == 0) {
        ws_url = "wss://" + ws_url.substr(8);
    }

    ws_url += "/v1/ws/party/" + party_id;

    // Create and connect WebSocket
    impl_->ws_client = std::make_unique<WebSocketWrapper>(ws_url, impl_->token);

    // Set up event handler
    impl_->ws_client->set_event_callback([this](const std::string& event, const json& data) {
        impl_->handle_ws_event(event, data);
    });

    impl_->ws_client->connect();
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
    impl_->match_found_callback = callback;
}

void Client::on_lobby_update(LobbyUpdateCallback callback) {
    impl_->lobby_update_callback = callback;
}

void Client::on_event(EventCallback callback) {
    impl_->event_callback = callback;
}

} // namespace game
