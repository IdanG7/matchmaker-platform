#pragma once

#include "types.hpp"
#include <httplib.h>
#include <optional>

namespace matchmaker {

/**
 * HTTP client wrapper for REST API calls.
 * Thread-safe for concurrent requests.
 */
class HTTPClient {
public:
    explicit HTTPClient(const std::string& base_url);
    ~HTTPClient() = default;

    // Authentication
    void set_auth_token(const std::string& token);
    void clear_auth_token();

    // HTTP methods
    Result<json> get(const std::string& path, const httplib::Params& params = {});
    Result<json> post(const std::string& path, const json& body);
    Result<json> patch(const std::string& path, const json& body);
    Result<json> del(const std::string& path);

    // Timeout configuration
    void set_timeout(int seconds);

private:
    std::string base_url_;
    std::string auth_token_;
    int timeout_seconds_ = 30;

    httplib::Headers get_headers() const;
    Result<json> handle_response(const httplib::Result& res);
};

} // namespace matchmaker
