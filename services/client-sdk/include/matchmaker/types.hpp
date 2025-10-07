#pragma once

#include <string>
#include <vector>
#include <functional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace matchmaker {

using json = nlohmann::json;

// ============================================================================
// Authentication Types
// ============================================================================

struct AuthTokens {
    std::string access_token;
    std::string refresh_token;
    std::string token_type = "Bearer";
};

struct RegisterRequest {
    std::string username;
    std::string email;
    std::string password;
    std::string region;
};

struct LoginRequest {
    std::string username;
    std::string password;
};

// ============================================================================
// Profile Types
// ============================================================================

struct ProfileInfo {
    std::string player_id;
    std::string username;
    std::string email;
    std::string region;
    int mmr;
    std::string created_at;
};

struct ProfileUpdateRequest {
    std::optional<std::string> region;
};

// ============================================================================
// Party Types
// ============================================================================

struct PartyMember {
    std::string player_id;
    std::string username;
    bool is_leader;
    bool is_ready;
};

struct PartyInfo {
    std::string party_id;
    std::string leader_id;
    std::string region;
    std::string status;  // idle, queueing, ready, in_match
    int size;
    int max_size;
    std::vector<PartyMember> members;
    std::string created_at;
};

struct QueueRequest {
    std::string mode;      // ranked, casual
    int team_size;         // 1, 5, etc.
};

// ============================================================================
// Session Types
// ============================================================================

struct SessionInfo {
    std::string match_id;
    std::string status;         // allocating, active, ended, cancelled
    std::string server_endpoint;
    std::string server_token;
    std::string region;
    std::string mode;
    std::vector<std::string> player_ids;
    std::string started_at;
};

struct MatchResult {
    std::string match_id;
    int winner_team;
    json player_stats;          // Optional player-specific stats
    int duration_seconds;
};

// ============================================================================
// Leaderboard Types
// ============================================================================

struct LeaderboardEntry {
    std::string player_id;
    std::string username;
    int rating;
    int rank;
    int wins;
    int losses;
    int games_played;
    double win_rate;
};

struct MatchHistoryEntry {
    std::string match_id;
    std::string played_at;
    std::string mode;
    std::string result;     // win, loss, draw
    int mmr_change;
    int team;
    json stats;
};

// ============================================================================
// Event Types
// ============================================================================

enum class EventType {
    // WebSocket connection events
    CONNECTED,
    DISCONNECTED,
    ERROR,

    // Party events
    MEMBER_JOINED,
    MEMBER_LEFT,
    MEMBER_READY,
    PARTY_UPDATED,

    // Queue events
    QUEUE_ENTERED,
    QUEUE_LEFT,
    MATCH_FOUND,

    // Session events
    SESSION_STARTED,
    SESSION_ENDED,

    // Unknown
    UNKNOWN
};

struct Event {
    EventType type;
    json data;
    std::chrono::system_clock::time_point timestamp;
};

// Event callback type
using EventCallback = std::function<void(const Event&)>;

// ============================================================================
// Error Handling
// ============================================================================

struct APIError {
    int status_code;
    std::string error;
    std::string detail;

    std::string to_string() const {
        return "HTTP " + std::to_string(status_code) + ": " + error +
               (detail.empty() ? "" : " - " + detail);
    }
};

// Result type for API calls
template<typename T>
struct Result {
    bool success;
    T value;
    APIError error;

    static Result<T> Success(T val) {
        return Result<T>{true, std::move(val), {}};
    }

    static Result<T> Failure(APIError err) {
        return Result<T>{false, T{}, std::move(err)};
    }

    explicit operator bool() const { return success; }
};

// Specialization for void returns
template<>
struct Result<void> {
    bool success;
    APIError error;

    static Result<void> Success() {
        return Result<void>{true, {}};
    }

    static Result<void> Failure(APIError err) {
        return Result<void>{false, std::move(err)};
    }

    explicit operator bool() const { return success; }
};

} // namespace matchmaker
