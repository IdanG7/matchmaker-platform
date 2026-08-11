#include "game/auth.hpp"
#include "url.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace game {

using detail::parse_url;

AuthResult Auth::login(const std::string& base_url,
                       const std::string& username,
                       const std::string& password) {
    try {
        auto parsed = parse_url(base_url);
        httplib::Client client(parsed.host, parsed.port);
        client.set_connection_timeout(5, 0); // 5 seconds

        json body = {
            {"username", username},
            {"password", password}
        };

        auto res = client.Post("/v1/auth/login",
                              body.dump(),
                              "application/json");

        if (!res) {
            return AuthResult{false, "", "", "Connection failed"};
        }

        if (res->status == 200) {
            auto response = json::parse(res->body);
            return AuthResult{
                true,
                response.value("access_token", ""),
                response.value("refresh_token", ""),
                ""
            };
        } else {
            try {
                auto error = json::parse(res->body);
                return AuthResult{false, "", "", error.value("detail", "Login failed")};
            } catch (const json::exception&) {
                return AuthResult{false, "", "", "Login failed (invalid server response)"};
            }
        }
    } catch (const std::exception& e) {
        return AuthResult{false, "", "", std::string("Exception: ") + e.what()};
    }
}

AuthResult Auth::register_user(const std::string& base_url,
                               const std::string& email,
                               const std::string& username,
                               const std::string& password,
                               const std::string& region) {
    try {
        auto parsed = parse_url(base_url);
        httplib::Client client(parsed.host, parsed.port);
        client.set_connection_timeout(5, 0);

        json body = {
            {"email", email},
            {"username", username},
            {"password", password},
            {"region", region}
        };

        auto res = client.Post("/v1/auth/register",
                              body.dump(),
                              "application/json");

        if (!res) {
            return AuthResult{false, "", "", "Connection failed"};
        }

        if (res->status == 200 || res->status == 201) {
            auto response = json::parse(res->body);
            return AuthResult{
                true,
                response.value("access_token", ""),
                response.value("refresh_token", ""),
                ""
            };
        } else {
            try {
                auto error = json::parse(res->body);
                return AuthResult{false, "", "", error.value("detail", "Registration failed")};
            } catch (const json::exception&) {
                return AuthResult{false, "", "", "Registration failed (invalid server response)"};
            }
        }
    } catch (const std::exception& e) {
        return AuthResult{false, "", "", std::string("Exception: ") + e.what()};
    }
}

AuthResult Auth::refresh(const std::string& base_url,
                        const std::string& refresh_token) {
    try {
        auto parsed = parse_url(base_url);
        httplib::Client client(parsed.host, parsed.port);
        client.set_connection_timeout(5, 0);

        json body = {
            {"refresh_token", refresh_token}
        };

        auto res = client.Post("/v1/auth/refresh",
                              body.dump(),
                              "application/json");

        if (!res) {
            return AuthResult{false, "", "", "Connection failed"};
        }

        if (res->status == 200) {
            auto response = json::parse(res->body);
            return AuthResult{
                true,
                response.value("access_token", ""),
                refresh_token, // Keep same refresh token
                ""
            };
        } else {
            try {
                auto error = json::parse(res->body);
                return AuthResult{false, "", "", error.value("detail", "Token refresh failed")};
            } catch (const json::exception&) {
                return AuthResult{false, "", "", "Token refresh failed (invalid server response)"};
            }
        }
    } catch (const std::exception& e) {
        return AuthResult{false, "", "", std::string("Exception: ") + e.what()};
    }
}

} // namespace game
