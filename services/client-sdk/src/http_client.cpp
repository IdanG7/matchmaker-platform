#include "matchmaker/http_client.hpp"
#include <sstream>

namespace matchmaker {

HTTPClient::HTTPClient(const std::string& base_url)
    : base_url_(base_url) {
}

void HTTPClient::set_auth_token(const std::string& token) {
    auth_token_ = token;
}

void HTTPClient::clear_auth_token() {
    auth_token_.clear();
}

void HTTPClient::set_timeout(int seconds) {
    timeout_seconds_ = seconds;
}

httplib::Headers HTTPClient::get_headers() const {
    httplib::Headers headers = {
        {"Content-Type", "application/json"},
        {"Accept", "application/json"}
    };

    if (!auth_token_.empty()) {
        headers.emplace("Authorization", "Bearer " + auth_token_);
    }

    return headers;
}

Result<json> HTTPClient::handle_response(const httplib::Result& res) {
    if (!res) {
        return Result<json>::Failure({
            0,
            "Connection error",
            "Failed to connect to server"
        });
    }

    // Parse response body as JSON
    json response_body;
    if (!res->body.empty()) {
        try {
            response_body = json::parse(res->body);
        } catch (const json::parse_error& e) {
            // Non-JSON response
            response_body = {{"message", res->body}};
        }
    }

    // Success responses (2xx)
    if (res->status >= 200 && res->status < 300) {
        return Result<json>::Success(response_body);
    }

    // Error responses (4xx, 5xx)
    APIError error;
    error.status_code = res->status;

    if (response_body.contains("error")) {
        error.error = response_body["error"];
    } else {
        error.error = "HTTP " + std::to_string(res->status);
    }

    if (response_body.contains("detail")) {
        error.detail = response_body["detail"];
    }

    return Result<json>::Failure(error);
}

Result<json> HTTPClient::get(const std::string& path, const httplib::Params& params) {
    httplib::Client client(base_url_);
    client.set_read_timeout(timeout_seconds_, 0);

    std::string query_string;
    if (!params.empty()) {
        std::ostringstream oss;
        bool first = true;
        for (const auto& [key, val] : params) {
            if (!first) oss << "&";
            oss << key << "=" << val;
            first = false;
        }
        query_string = "?" + oss.str();
    }

    auto res = client.Get((path + query_string).c_str(), get_headers());
    return handle_response(res);
}

Result<json> HTTPClient::post(const std::string& path, const json& body) {
    httplib::Client client(base_url_);
    client.set_read_timeout(timeout_seconds_, 0);

    auto res = client.Post(
        path.c_str(),
        get_headers(),
        body.dump(),
        "application/json"
    );

    return handle_response(res);
}

Result<json> HTTPClient::patch(const std::string& path, const json& body) {
    httplib::Client client(base_url_);
    client.set_read_timeout(timeout_seconds_, 0);

    auto res = client.Patch(
        path.c_str(),
        get_headers(),
        body.dump(),
        "application/json"
    );

    return handle_response(res);
}

Result<json> HTTPClient::del(const std::string& path) {
    httplib::Client client(base_url_);
    client.set_read_timeout(timeout_seconds_, 0);

    auto res = client.Delete(path.c_str(), get_headers());
    return handle_response(res);
}

} // namespace matchmaker
