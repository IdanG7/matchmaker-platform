#pragma once

// Internal helper shared by auth.cpp and client.cpp. Not part of the public
// headers installed under include/game.

#include <string>
#include <stdexcept>

namespace game {
namespace detail {

struct ParsedURL {
    std::string scheme;
    std::string host;
    int port;
};

// Splits "http://host:port/whatever" into its parts. Falls back to
// http://localhost:8080 when the input carries no scheme.
inline ParsedURL parse_url(const std::string& url) {
    ParsedURL result{"http", "localhost", 8080};

    const std::size_t scheme_end = url.find("://");
    if (scheme_end == std::string::npos) return result;

    result.scheme = url.substr(0, scheme_end);
    const std::size_t host_start = scheme_end + 3;

    // Stop at the first '/' so a base_url with a trailing path or slash does
    // not end up inside the host.
    const std::size_t path_start = url.find('/', host_start);
    const std::string authority = url.substr(
        host_start,
        path_start == std::string::npos ? std::string::npos : path_start - host_start);

    const std::size_t colon = authority.rfind(':');
    if (colon != std::string::npos) {
        result.host = authority.substr(0, colon);
        try {
            result.port = std::stoi(authority.substr(colon + 1));
        } catch (const std::exception&) {
            result.port = (result.scheme == "https") ? 443 : 80;
        }
    } else {
        result.host = authority;
        result.port = (result.scheme == "https") ? 443 : 80;
    }
    return result;
}

} // namespace detail
} // namespace game
