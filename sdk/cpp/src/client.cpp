#include "game/client.hpp"

namespace game {

// Placeholder implementation
// To be implemented in Phase 7

class Client::Impl {
public:
    std::string base_url;
    std::string token;
};

Client::Client(const std::string& base_url, const std::string& token)
    : impl_(std::make_unique<Impl>()) {
    impl_->base_url = base_url;
    impl_->token = token;
}

Client::~Client() = default;

Profile Client::get_profile() {
    // TODO: Implement REST call
    return Profile{};
}

void Client::update_profile(const Profile& profile) {
    (void)profile;
    // TODO: Implement
}

Party Client::create_party() {
    // TODO: Implement
    return Party{};
}

void Client::join_party(const std::string& party_id) {
    (void)party_id;
    // TODO: Implement
}

void Client::leave_party(const std::string& party_id) {
    (void)party_id;
    // TODO: Implement
}

void Client::ready() {
    // TODO: Implement
}

void Client::enqueue(const std::string& party_id, const std::string& mode, int team_size) {
    (void)party_id;
    (void)mode;
    (void)team_size;
    // TODO: Implement
}

void Client::cancel_queue(const std::string& party_id) {
    (void)party_id;
    // TODO: Implement
}

void Client::connect_ws() {
    // TODO: Implement WebSocket connection
}

void Client::disconnect_ws() {
    // TODO: Implement
}

void Client::on_match_found(MatchFoundCallback callback) {
    (void)callback;
    // TODO: Store callback and invoke when match found event received
}

void Client::on_lobby_update(LobbyUpdateCallback callback) {
    (void)callback;
    // TODO: Store callback and invoke when lobby update event received
}

void Client::on_event(EventCallback callback) {
    (void)callback;
    // TODO: Store callback and invoke for all events
}

} // namespace game
