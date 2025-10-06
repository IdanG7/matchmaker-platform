#pragma once

#include <string>
#include <vector>
#include <functional>
#include <memory>

namespace game {

// Player profile
struct Profile {
    std::string id;
    std::string username;
    std::string email;
    std::string region;
    int mmr;
};

// Party/Lobby
struct Party {
    std::string id;
    std::string leader_id;
    std::vector<std::string> member_ids;
    std::string status;
};

// Match info
struct MatchInfo {
    std::string match_id;
    std::string server_endpoint;
    std::string token;
    std::vector<std::vector<std::string>> teams;
};

// WebSocket event types
enum class EventType {
    PresenceHeartbeat,
    LobbyUpdate,
    MatchFound,
    SessionStarted,
    SessionEnded,
    Error
};

// WebSocket event
struct Event {
    EventType type;
    std::string data; // JSON payload
};

// Callbacks
using EventCallback = std::function<void(const Event&)>;
using MatchFoundCallback = std::function<void(const MatchInfo&)>;
using LobbyUpdateCallback = std::function<void(const Party&)>;

} // namespace game
