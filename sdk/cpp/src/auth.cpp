#include "game/auth.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace game {

namespace {
    // Helper to parse URL into host and port
    struct ParsedURL {
        std::string scheme;
        std::string host;
        int port;
    };

    ParsedURL parse_url(const std::string& url) {
        ParsedURL result;

        // Simple URL parsing (assumes http://host:port format)
        size_t scheme_end = url.find("://");
        if (scheme_end != std::string::npos) {
            result.scheme = url.substr(0, scheme_end);
            size_t host_start = scheme_end + 3;
            size_t port_start = url.find(":", host_start);

            if (port_start != std::string::npos) {
                result.host = url.substr(host_start, port_start - host_start);
                result.port = std::stoi(url.substr(port_start + 1));
            } else {
                result.host = url.substr(host_start);
                result.port = (result.scheme == "https") ? 443 : 80;
            }
        } else {
            // No scheme, assume http://localhost:8080
            result.scheme = "http";
            result.host = "localhost";
            result.port = 8080;
        }

        return result;
    }
}

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
                response["access_token"],
                response["refresh_token"],
                ""
            };
        } else {
            auto error = json::parse(res->body);
            return AuthResult{
                false,
                "",
                "",
                error.value("detail", "Login failed")
            };
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
                response["access_token"],
                response["refresh_token"],
                ""
            };
        } else {
            auto error = json::parse(res->body);
            return AuthResult{
                false,
                "",
                "",
                error.value("detail", "Registration failed")
            };
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
                response["access_token"],
                refresh_token, // Keep same refresh token
                ""
            };
        } else {
            auto error = json::parse(res->body);
            return AuthResult{
                false,
                "",
                "",
                error.value("detail", "Token refresh failed")
            };
        }
    } catch (const std::exception& e) {
        return AuthResult{false, "", "", std::string("Exception: ") + e.what()};
    }
}

} // namespace game
