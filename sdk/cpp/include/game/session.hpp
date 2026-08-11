#pragma once

#include <string>

namespace game {

// Result of a finished match, as reported by the game server that ran it.
struct MatchResultReport {
    std::string match_id;
    int winner_team = 0;      // 0-based team index
    int duration_seconds = 0;

    // Per-player stats keyed by player id, as a JSON object. Stored verbatim
    // by the API, so the shape is up to the game.
    std::string player_stats_json = "{}";
};

// Calls the game server makes against /v1/session.
//
// These are not player endpoints and take no bearer token: they are for the
// process running the match. Reporting a result is what ends the session,
// settles MMR and writes match history, so a server that never calls it
// leaves the match active forever and the leaderboard empty.
//
// Neither throws; both return false and fill `error` when given one.
class Session {
public:
    static bool submit_result(const std::string& base_url,
                              const MatchResultReport& result,
                              std::string* error = nullptr);

    // Tells the API the match is still alive. Optional, but without it a
    // crashed server cannot be told apart from a slow one.
    static bool heartbeat(const std::string& base_url,
                          const std::string& match_id,
                          const std::string& server_id,
                          int active_players,
                          std::string* error = nullptr);
};

} // namespace game
