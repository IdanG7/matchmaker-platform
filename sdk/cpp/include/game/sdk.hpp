#pragma once

#include "types.hpp"
#include "client.hpp"
#include "auth.hpp"
#include "session.hpp"

namespace game {

// Entry point to the matchmaker platform.
//
// Typical use:
//     game::SDK sdk("http://localhost:8080");
//     auto auth = sdk.login("player1", "password123");
//     if (!auth.success) { /* auth.error */ }
//     auto party = sdk.client().create_party();
class SDK {
public:
    explicit SDK(const std::string& base_url);
    ~SDK();

    SDK(const SDK&) = delete;
    SDK& operator=(const SDK&) = delete;

    // Authentication. On success the returned token is stored and used by
    // client() automatically. Neither throws; check AuthResult::success.
    AuthResult login(const std::string& username, const std::string& password);
    AuthResult register_user(const std::string& email,
                             const std::string& username,
                             const std::string& password,
                             const std::string& region = "us-west");

    // Use a token obtained elsewhere (e.g. restored from disk).
    void set_token(const std::string& token);
    const std::string& token() const;
    bool is_authenticated() const;

    // Authenticated API client. Valid until the token changes.
    Client& client();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace game
