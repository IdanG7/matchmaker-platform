#include <gtest/gtest.h>
#include "game/sdk.hpp"
#include "game/auth.hpp"
#include "game/client.hpp"

// Unit tests for C++ SDK
// Note: These tests don't require a running server - they test SDK construction
// and connection failure handling. For integration tests with a real server,
// see examples/party_test.cpp

TEST(AuthTest, LoginFailsWithoutServer) {
    // Auth functions should gracefully handle connection failures
    auto result = game::Auth::login("http://localhost:8080", "testuser", "password");
    EXPECT_FALSE(result.success);
    EXPECT_EQ(result.error, "Connection failed");
    EXPECT_TRUE(result.access_token.empty());
    EXPECT_TRUE(result.refresh_token.empty());
}

TEST(AuthTest, RegisterFailsWithoutServer) {
    // Register should gracefully handle connection failures
    auto result = game::Auth::register_user("http://localhost:8080", "user@test.com",
                                           "testuser", "password", "us-west");
    EXPECT_FALSE(result.success);
    EXPECT_EQ(result.error, "Connection failed");
}

TEST(AuthTest, RefreshFailsWithoutServer) {
    // Refresh should gracefully handle connection failures
    auto result = game::Auth::refresh("http://localhost:8080", "refresh_token");
    EXPECT_FALSE(result.success);
    EXPECT_EQ(result.error, "Connection failed");
}

TEST(SDKTest, CanConstruct) {
    // SDK construction should not throw
    game::SDK sdk("http://localhost:8080");
    EXPECT_TRUE(true);
}

TEST(SDKTest, CanSetToken) {
    // Setting a token should not throw
    game::SDK sdk("http://localhost:8080");
    sdk.set_token("test_token");
    EXPECT_TRUE(true);
}

TEST(SDKTest, CanGetClient) {
    // Getting a client instance should work
    game::SDK sdk("http://localhost:8080");
    sdk.set_token("test_token");
    auto& client = sdk.client();
    // Just verify we can get a reference without crashing
    (void)client; // Suppress unused variable warning
    EXPECT_TRUE(true);
}

TEST(ClientTest, CanConstruct) {
    // Client construction should not throw
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_TRUE(true);
}

TEST(ClientTest, GetProfileThrowsWithoutServer) {
    // Client methods should throw when server is unavailable
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_THROW(client.get_profile(), std::runtime_error);
}

TEST(ClientTest, CreatePartyThrowsWithoutServer) {
    // Client methods should throw when server is unavailable
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_THROW(client.create_party(), std::runtime_error);
}

TEST(ClientTest, WebSocketNotConnectedByDefault) {
    // WebSocket should not be connected by default
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_FALSE(client.is_ws_connected());
}

TEST(ClientTest, CanSetCallbacks) {
    // Setting callbacks should not throw
    game::Client client("http://localhost:8080", "test_token");

    client.on_match_found([](const game::MatchInfo&) {
        // Callback
    });

    client.on_lobby_update([](const game::Party&) {
        // Callback
    });

    EXPECT_TRUE(true);
}

// Note: For comprehensive integration tests that require a running server,
// see the SDK E2E test in CI/CD or run examples/party_test manually.
