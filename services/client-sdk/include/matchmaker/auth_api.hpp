#pragma once

#include "types.hpp"
#include "http_client.hpp"
#include <memory>

namespace matchmaker {

/**
 * Authentication API wrapper.
 * Handles registration, login, token refresh.
 */
class AuthAPI {
public:
    explicit AuthAPI(std::shared_ptr<HTTPClient> http_client);
    ~AuthAPI() = default;

    /**
     * Register a new user account.
     *
     * @param request Registration details (username, email, password, region)
     * @return AuthTokens on success, error on failure
     */
    Result<AuthTokens> register_user(const RegisterRequest& request);

    /**
     * Login with username and password.
     *
     * @param request Login credentials (username, password)
     * @return AuthTokens on success, error on failure
     */
    Result<AuthTokens> login(const LoginRequest& request);

    /**
     * Refresh access token using refresh token.
     *
     * @param refresh_token The refresh token from previous login
     * @return New AuthTokens on success, error on failure
     */
    Result<AuthTokens> refresh_token(const std::string& refresh_token);

private:
    std::shared_ptr<HTTPClient> http_;
};

} // namespace matchmaker
