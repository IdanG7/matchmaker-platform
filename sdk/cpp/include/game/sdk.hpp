#pragma once

#include "types.hpp"
#include "client.hpp"
#include "auth.hpp"

namespace game {

// Main SDK entry point
class SDK {
public:
    SDK(const std::string& base_url);
    ~SDK();

    // Authentication
    AuthResult authenticate(const std::string& email, const std::string& password);
    void set_token(const std::string& token);

    // Get client instance
    Client& client();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace game
