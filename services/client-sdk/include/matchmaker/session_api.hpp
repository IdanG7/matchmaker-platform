#pragma once

#include "types.hpp"
#include "http_client.hpp"
#include <memory>

namespace matchmaker {

/**
 * Session API wrapper.
 * Handles game session details, heartbeats, and result reporting.
 */
class SessionAPI {
public:
    explicit SessionAPI(std::shared_ptr<HTTPClient> http_client);
    ~SessionAPI() = default;

    /**
     * Get session details for a match.
     *
     * @param match_id The match ID
     * @return SessionInfo on success, error on failure
     */
    Result<SessionInfo> get_session(const std::string& match_id);

    /**
     * Send heartbeat to keep session alive.
     *
     * @param match_id The match ID
     * @return Success or error
     */
    Result<void> send_heartbeat(const std::string& match_id);

    /**
     * Submit match result (game server only).
     *
     * @param result Match result details
     * @return Success or error
     */
    Result<void> submit_result(const MatchResult& result);

private:
    std::shared_ptr<HTTPClient> http_;
};

} // namespace matchmaker
