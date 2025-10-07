#include "matchmaker/auth_api.hpp"

namespace matchmaker {

AuthAPI::AuthAPI(std::shared_ptr<HTTPClient> http_client)
    : http_(std::move(http_client)) {
}

Result<AuthTokens> AuthAPI::register_user(const RegisterRequest& request) {
    json body = {
        {"username", request.username},
        {"email", request.email},
        {"password", request.password},
        {"region", request.region}
    };

    auto result = http_->post("/v1/auth/register", body);

    if (!result) {
        return Result<AuthTokens>::Failure(result.error);
    }

    AuthTokens tokens;
    tokens.access_token = result.value["access_token"];
    tokens.refresh_token = result.value["refresh_token"];
    tokens.token_type = result.value["token_type"];

    return Result<AuthTokens>::Success(tokens);
}

Result<AuthTokens> AuthAPI::login(const LoginRequest& request) {
    json body = {
        {"username", request.username},
        {"password", request.password}
    };

    auto result = http_->post("/v1/auth/login", body);

    if (!result) {
        return Result<AuthTokens>::Failure(result.error);
    }

    AuthTokens tokens;
    tokens.access_token = result.value["access_token"];
    tokens.refresh_token = result.value["refresh_token"];
    tokens.token_type = result.value["token_type"];

    return Result<AuthTokens>::Success(tokens);
}

Result<AuthTokens> AuthAPI::refresh_token(const std::string& refresh_token) {
    json body = {
        {"refresh_token", refresh_token}
    };

    auto result = http_->post("/v1/auth/refresh", body);

    if (!result) {
        return Result<AuthTokens>::Failure(result.error);
    }

    AuthTokens tokens;
    tokens.access_token = result.value["access_token"];
    tokens.refresh_token = result.value["refresh_token"];
    tokens.token_type = result.value["token_type"];

    return Result<AuthTokens>::Success(tokens);
}

} // namespace matchmaker
