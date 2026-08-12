#pragma once

#include "types.hpp"
#include <memory>

namespace game {

// Authenticated client for the matchmaker REST API and the party WebSocket.
//
// Every method throws std::runtime_error on transport failure or a non-success
// status, with the API's "detail" message when one is present.
class Client {
public:
    Client(const std::string& base_url, const std::string& token);
    ~Client();

    // The bearer token this client authenticates with.
    const std::string& token() const;

    // Profile operations
    Profile get_profile();
    void update_profile(const Profile& profile);

    // Party operations
    Party create_party();
    Party get_party(const std::string& party_id);
    Party join_party(const std::string& party_id);
    void leave_party(const std::string& party_id);

    // Toggles the caller's ready flag and returns the party's ready tally.
    // Note the API readies whoever creates a party, so calling this blindly
    // after create_party un-readies you. Prefer set_ready.
    ReadyCheck toggle_ready(const std::string& party_id);

    // Drives the caller's ready flag to a specific value, toggling only when
    // it differs. Safe to call repeatedly.
    ReadyCheck set_ready(const std::string& party_id, bool ready);

    // Matchmaking. Both return the updated party.
    Party enqueue(const std::string& party_id, const std::string& mode, int team_size);
    Party cancel_queue(const std::string& party_id);

    // WebSocket connection. Match and lobby events arrive on the callbacks
    // below, so register those before connecting.
    void connect_ws(const std::string& party_id);
    void disconnect_ws();
    bool is_ws_connected() const;

    // Delivers any WebSocket events that have arrived.
    //
    // Native builds dispatch from the socket's own thread, so this does
    // nothing and calling it is harmless. Browser builds have no threads and
    // dispatch only from here, so a WASM client that never calls this never
    // learns that its match was found. Call it from the main loop, not from
    // inside another SDK call: under Asyncify the callbacks may make blocking
    // calls of their own, and starting one while another is suspended traps
    // the module.
    void poll();

    // Event callbacks. Invoked from poll() in the browser, and on the
    // WebSocket thread natively.
    void on_match_found(MatchFoundCallback callback);
    void on_lobby_update(LobbyUpdateCallback callback);
    void on_event(EventCallback callback);

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace game
