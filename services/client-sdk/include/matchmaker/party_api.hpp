#pragma once

#include "types.hpp"
#include "http_client.hpp"
#include <memory>

namespace matchmaker {

/**
 * Party/Lobby API wrapper.
 * Handles party creation, joining, ready checks, and queue operations.
 */
class PartyAPI {
public:
    explicit PartyAPI(std::shared_ptr<HTTPClient> http_client);
    ~PartyAPI() = default;

    /**
     * Create a new party.
     *
     * @param max_size Maximum number of players (1-10)
     * @return PartyInfo on success, error on failure
     */
    Result<PartyInfo> create_party(int max_size = 5);

    /**
     * Join an existing party.
     *
     * @param party_id The party ID to join
     * @return PartyInfo on success, error on failure
     */
    Result<PartyInfo> join_party(const std::string& party_id);

    /**
     * Leave current party.
     *
     * @param party_id The party ID to leave
     * @return Success or error
     */
    Result<void> leave_party(const std::string& party_id);

    /**
     * Toggle ready status in party.
     *
     * @param party_id The party ID
     * @param ready Ready status (true = ready, false = not ready)
     * @return PartyInfo on success, error on failure
     */
    Result<PartyInfo> set_ready(const std::string& party_id, bool ready);

    /**
     * Get current party details.
     *
     * @param party_id The party ID
     * @return PartyInfo on success, error on failure
     */
    Result<PartyInfo> get_party(const std::string& party_id);

    /**
     * Enter matchmaking queue.
     *
     * @param request Queue parameters (mode, team_size)
     * @return Success or error
     */
    Result<PartyInfo> enter_queue(const std::string& party_id, const QueueRequest& request);

    /**
     * Leave matchmaking queue.
     *
     * @return Success or error
     */
    Result<PartyInfo> leave_queue(const std::string& party_id);

private:
    std::shared_ptr<HTTPClient> http_;
};

} // namespace matchmaker
