#include "game/auth.hpp"
#include "transport.hpp"
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace game {
namespace {

// The three auth calls differ only in path, body and the wording of a
// failure, so they share one implementation.
AuthResult post_auth(const std::string& base_url,
                     const std::string& path,
                     const json& body,
                     const std::string& failure) {
    try {
        const detail::Headers headers = {{"Content-Type", "application/json"}};
        const auto res =
            detail::http_request(base_url, "POST", path, body.dump(), headers);

        if (!res.transport_ok) {
            // Kept as the exact string "Connection failed": the SDK's tests
            // assert on it to tell an unreachable server apart from a
            // rejected request.
            return AuthResult{false, "", "", "Connection failed"};
        }

        if (res.status >= 200 && res.status < 300) {
            const auto response = json::parse(res.body);
            return AuthResult{true,
                              response.value("access_token", ""),
                              response.value("refresh_token", ""),
                              ""};
        }

        try {
            const auto error = json::parse(res.body);
            if (error.contains("detail")) {
                const auto& d = error["detail"];
                return AuthResult{false, "", "",
                                  d.is_string() ? d.get<std::string>() : d.dump()};
            }
        } catch (const json::exception&) {
            // fall through to the generic message
        }
        return AuthResult{false, "", "", failure + " (invalid server response)"};

    } catch (const std::exception& e) {
        return AuthResult{false, "", "", std::string("Exception: ") + e.what()};
    }
}

} // namespace

AuthResult Auth::login(const std::string& base_url,
                       const std::string& username,
                       const std::string& password) {
    return post_auth(base_url, "/v1/auth/login",
                     {{"username", username}, {"password", password}}, "Login failed");
}

AuthResult Auth::register_user(const std::string& base_url,
                               const std::string& email,
                               const std::string& username,
                               const std::string& password,
                               const std::string& region) {
    return post_auth(base_url, "/v1/auth/register",
                     {{"email", email},
                      {"username", username},
                      {"password", password},
                      {"region", region}},
                     "Registration failed");
}

AuthResult Auth::refresh(const std::string& base_url,
                         const std::string& refresh_token) {
    return post_auth(base_url, "/v1/auth/refresh",
                     {{"refresh_token", refresh_token}}, "Token refresh failed");
}

} // namespace game
