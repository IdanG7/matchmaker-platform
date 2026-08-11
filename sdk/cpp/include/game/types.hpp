#pragma once

#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <cstdint>

namespace game {

// Player profile
struct Profile {
    std::string id;
    std::string username;
    std::string email;
    std::string region;
    int mmr = 0;
    // The party this player is already in, empty if none. A client that
    // reconnects needs this to rejoin or leave: create_party is refused while
    // it holds one, and there is no other way to learn the id.
    std::string party_id;
};

// A single member of a party. Mirrors PartyMemberResponse in the API.
struct PartyMember {
    std::string player_id;
    std::string username;
    std::string joined_at;
    bool ready = false;
    std::string role;
};

// Party/Lobby. Mirrors PartyResponse in the API.
struct Party {
    std::string id;
    std::string leader_id;
    std::string region;
    int size = 0;
    int max_size = 0;
    std::string status;      // idle, queueing, ready, in_match, disbanded
    std::string queue_mode;  // empty unless queueing
    int team_size = 0;
    std::vector<PartyMember> members;
};

// Result of toggling ready state. Mirrors ReadyCheckResponse in the API.
struct ReadyCheck {
    std::string party_id;
    int ready_count = 0;
    int total_count = 0;
    bool all_ready = false;
    std::vector<std::string> not_ready_players;
};

// Match info delivered on the match_found event.
struct MatchInfo {
    std::string match_id;
    std::string server_endpoint;  // "host:port"
    std::string server_token;     // HMAC session token, present it to the game server
    std::string region;
    std::string mode;
    std::vector<std::vector<std::string>> teams;  // teams[i] = player ids on team i

    // server_endpoint split for callers that need to open a socket. Returns
    // false when the endpoint is missing or malformed.
    bool split_endpoint(std::string& host, uint16_t& port) const;
};

// What changed in the party. The server sends deltas rather than whole-party
// snapshots, so this describes the change; call get_party() when you need the
// full state afterwards.
enum class LobbyChange {
    MemberJoined,
    MemberLeft,
    MemberReady,
    QueueEntered,
    QueueLeft,
    PartyUpdated
};

struct LobbyEvent {
    LobbyChange change;
    std::string party_id;

    // MemberJoined / MemberLeft / MemberReady
    std::string player_id;
    std::string username;
    bool ready = false;  // MemberReady only

    // QueueEntered
    std::string mode;
    int team_size = 0;

    // PartyUpdated carries a full party; empty for every other change.
    Party party;
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

// Raw WebSocket event, for callers that want the untouched payload.
struct Event {
    EventType type;
    std::string name; // server event name, e.g. "member_joined"
    std::string data; // JSON payload
};

// Callbacks
using EventCallback = std::function<void(const Event&)>;
using MatchFoundCallback = std::function<void(const MatchInfo&)>;
using LobbyUpdateCallback = std::function<void(const LobbyEvent&)>;

} // namespace game
