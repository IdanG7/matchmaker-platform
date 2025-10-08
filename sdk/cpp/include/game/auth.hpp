#pragma once

#include <string>

namespace game {

// Auth result
struct AuthResult {
    bool success;
    std::string access_token;
    std::string refresh_token;
    std::string error;
};

// Auth operations (to be implemented in Phase 7)
class Auth {
public:
    static AuthResult login(const std::string& base_url,
                           const std::string& username,
                           const std::string& password);

    static AuthResult register_user(const std::string& base_url,
                                    const std::string& email,
                                    const std::string& username,
                                    const std::string& password,
                                    const std::string& region);

    static AuthResult refresh(const std::string& base_url,
                             const std::string& refresh_token);
};

} // namespace game
