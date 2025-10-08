#pragma once

#include "types.hpp"
#include <memory>

namespace game {

// Main game client (to be implemented in Phase 7)
class Client {
public:
    Client(const std::string& base_url, const std::string& token);
    ~Client();

    // Profile operations
    Profile get_profile();
    void update_profile(const Profile& profile);

    // Party operations
    Party create_party();
    void join_party(const std::string& party_id);
    void leave_party(const std::string& party_id);
    void ready();

    // Matchmaking
    void enqueue(const std::string& party_id, const std::string& mode, int team_size);
    void cancel_queue(const std::string& party_id);

    // WebSocket connection
    void connect_ws(const std::string& party_id);
    void disconnect_ws();
    bool is_ws_connected() const;

    // Event callbacks
    void on_match_found(MatchFoundCallback callback);
    void on_lobby_update(LobbyUpdateCallback callback);
    void on_event(EventCallback callback);

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace game
