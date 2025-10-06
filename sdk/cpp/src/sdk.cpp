#include "game/sdk.hpp"

namespace game {

// Placeholder implementation
// To be implemented in Phase 7

class SDK::Impl {
public:
    std::string base_url;
    std::string token;
    std::unique_ptr<Client> client;
};

SDK::SDK(const std::string& base_url) : impl_(std::make_unique<Impl>()) {
    impl_->base_url = base_url;
}

SDK::~SDK() = default;

AuthResult SDK::authenticate(const std::string& email, const std::string& password) {
    // TODO: Implement
    return AuthResult{false, "", "", "Not implemented"};
}

void SDK::set_token(const std::string& token) {
    impl_->token = token;
}

Client& SDK::client() {
    if (!impl_->client) {
        impl_->client = std::make_unique<Client>(impl_->base_url, impl_->token);
    }
    return *impl_->client;
}

} // namespace game
