#include "game/sdk.hpp"

namespace game {

class SDK::Impl {
public:
    std::string base_url;
    std::string token;
    std::unique_ptr<Client> client;

    // The Client captures the token at construction, so any token change has
    // to invalidate the cached instance or later calls keep using the old one.
    void set_token(const std::string& value) {
        if (token == value) return;
        token = value;
        client.reset();
    }
};

SDK::SDK(const std::string& base_url) : impl_(std::make_unique<Impl>()) {
    impl_->base_url = base_url;
}

SDK::~SDK() = default;

AuthResult SDK::login(const std::string& username, const std::string& password) {
    auto result = Auth::login(impl_->base_url, username, password);
    if (result.success) {
        impl_->set_token(result.access_token);
    }
    return result;
}

AuthResult SDK::register_user(const std::string& email,
                              const std::string& username,
                              const std::string& password,
                              const std::string& region) {
    auto result = Auth::register_user(impl_->base_url, email, username, password, region);
    if (result.success) {
        impl_->set_token(result.access_token);
    }
    return result;
}

void SDK::set_token(const std::string& token) {
    impl_->set_token(token);
}

const std::string& SDK::token() const {
    return impl_->token;
}

bool SDK::is_authenticated() const {
    return !impl_->token.empty();
}

Client& SDK::client() {
    if (!impl_->client) {
        impl_->client = std::make_unique<Client>(impl_->base_url, impl_->token);
    }
    return *impl_->client;
}

} // namespace game
