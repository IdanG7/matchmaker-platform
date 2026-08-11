#include <gtest/gtest.h>
#include "game/sdk.hpp"
#include "game/auth.hpp"
#include "game/client.hpp"
#include "../src/url.hpp"

// Unit tests for the C++ SDK. These do not require a running server: they
// cover URL/endpoint parsing and the graceful-failure paths. The end-to-end
// flow against a live stack is covered by examples/party_test.cpp and by the
// SDK/API route contract test in tests/contract/.

// --- Auth failure handling -------------------------------------------------

TEST(AuthTest, LoginFailsWithoutServer) {
    auto result = game::Auth::login("http://localhost:8080", "testuser", "password");
    EXPECT_FALSE(result.success);
    EXPECT_EQ(result.error, "Connection failed");
    EXPECT_TRUE(result.access_token.empty());
    EXPECT_TRUE(result.refresh_token.empty());
}

TEST(AuthTest, RegisterFailsWithoutServer) {
    auto result = game::Auth::register_user("http://localhost:8080", "user@test.com",
                                            "testuser", "password", "us-west");
    EXPECT_FALSE(result.success);
    EXPECT_EQ(result.error, "Connection failed");
}

TEST(AuthTest, RefreshFailsWithoutServer) {
    auto result = game::Auth::refresh("http://localhost:8080", "refresh_token");
    EXPECT_FALSE(result.success);
    EXPECT_EQ(result.error, "Connection failed");
}

// --- URL parsing -----------------------------------------------------------

TEST(UrlTest, ParsesHostAndExplicitPort) {
    const auto parsed = game::detail::parse_url("http://example.com:8080");
    EXPECT_EQ(parsed.scheme, "http");
    EXPECT_EQ(parsed.host, "example.com");
    EXPECT_EQ(parsed.port, 8080);
}

TEST(UrlTest, DefaultsHttpPortTo80) {
    const auto parsed = game::detail::parse_url("http://example.com");
    EXPECT_EQ(parsed.host, "example.com");
    EXPECT_EQ(parsed.port, 80);
}

TEST(UrlTest, DefaultsHttpsPortTo443) {
    const auto parsed = game::detail::parse_url("https://example.com");
    EXPECT_EQ(parsed.scheme, "https");
    EXPECT_EQ(parsed.host, "example.com");
    EXPECT_EQ(parsed.port, 443);
}

// A trailing slash or path used to be swallowed into the host, producing a
// hostname like "example.com/" that never resolves.
TEST(UrlTest, TrailingSlashDoesNotLeakIntoHost) {
    const auto parsed = game::detail::parse_url("http://example.com:8080/");
    EXPECT_EQ(parsed.host, "example.com");
    EXPECT_EQ(parsed.port, 8080);
}

TEST(UrlTest, PathDoesNotLeakIntoHost) {
    const auto parsed = game::detail::parse_url("https://api.example.com/v1/base");
    EXPECT_EQ(parsed.host, "api.example.com");
    EXPECT_EQ(parsed.port, 443);
}

TEST(UrlTest, FallsBackWhenSchemeMissing) {
    const auto parsed = game::detail::parse_url("example.com:9000");
    EXPECT_EQ(parsed.host, "localhost");
    EXPECT_EQ(parsed.port, 8080);
}

// --- MatchInfo::split_endpoint --------------------------------------------

TEST(MatchInfoTest, SplitsHostAndPort) {
    game::MatchInfo match;
    match.server_endpoint = "gameserver-1.example.com:9100";

    std::string host;
    uint16_t port = 0;
    ASSERT_TRUE(match.split_endpoint(host, port));
    EXPECT_EQ(host, "gameserver-1.example.com");
    EXPECT_EQ(port, 9100);
}

TEST(MatchInfoTest, RejectsEndpointWithoutPort) {
    game::MatchInfo match;
    match.server_endpoint = "gameserver-1.example.com";

    std::string host;
    uint16_t port = 0;
    EXPECT_FALSE(match.split_endpoint(host, port));
}

TEST(MatchInfoTest, RejectsEmptyEndpoint) {
    game::MatchInfo match;
    std::string host;
    uint16_t port = 0;
    EXPECT_FALSE(match.split_endpoint(host, port));
}

TEST(MatchInfoTest, RejectsNonNumericPort) {
    game::MatchInfo match;
    match.server_endpoint = "host:notaport";

    std::string host;
    uint16_t port = 0;
    EXPECT_FALSE(match.split_endpoint(host, port));
}

TEST(MatchInfoTest, RejectsOutOfRangePort) {
    game::MatchInfo match;
    match.server_endpoint = "host:70000";

    std::string host;
    uint16_t port = 0;
    EXPECT_FALSE(match.split_endpoint(host, port));
}

TEST(MatchInfoTest, RejectsPortZero) {
    game::MatchInfo match;
    match.server_endpoint = "host:0";

    std::string host;
    uint16_t port = 0;
    EXPECT_FALSE(match.split_endpoint(host, port));
}

// --- SDK lifecycle ---------------------------------------------------------

TEST(SDKTest, CanConstruct) {
    EXPECT_NO_THROW(game::SDK sdk("http://localhost:8080"));
}

TEST(SDKTest, StartsUnauthenticated) {
    game::SDK sdk("http://localhost:8080");
    EXPECT_FALSE(sdk.is_authenticated());
    EXPECT_TRUE(sdk.token().empty());
}

TEST(SDKTest, SetTokenMarksAuthenticated) {
    game::SDK sdk("http://localhost:8080");
    sdk.set_token("test_token");
    EXPECT_TRUE(sdk.is_authenticated());
    EXPECT_EQ(sdk.token(), "test_token");
}

// The client caches the token it was constructed with, so changing the token
// has to hand back a rebuilt client rather than one still using the old one.
TEST(SDKTest, ChangingTokenRebuildsClient) {
    game::SDK sdk("http://localhost:8080");
    sdk.set_token("first_token");
    game::Client* first = &sdk.client();

    sdk.set_token("second_token");
    game::Client* second = &sdk.client();

    EXPECT_NE(first, second);
}

TEST(SDKTest, SettingSameTokenKeepsClient) {
    game::SDK sdk("http://localhost:8080");
    sdk.set_token("same_token");
    game::Client* first = &sdk.client();

    sdk.set_token("same_token");
    EXPECT_EQ(first, &sdk.client());
}

TEST(SDKTest, LoginFailsWithoutServer) {
    game::SDK sdk("http://localhost:8080");
    auto result = sdk.login("testuser", "password");
    EXPECT_FALSE(result.success);
    EXPECT_FALSE(sdk.is_authenticated());
}

// --- Client ----------------------------------------------------------------

TEST(ClientTest, CanConstruct) {
    EXPECT_NO_THROW(game::Client client("http://localhost:8080", "test_token"));
}

TEST(ClientTest, GetProfileThrowsWithoutServer) {
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_THROW(client.get_profile(), std::runtime_error);
}

TEST(ClientTest, CreatePartyThrowsWithoutServer) {
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_THROW(client.create_party(), std::runtime_error);
}

TEST(ClientTest, PartyOperationsThrowWithoutServer) {
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_THROW(client.get_party("party-1"), std::runtime_error);
    EXPECT_THROW(client.join_party("party-1"), std::runtime_error);
    EXPECT_THROW(client.leave_party("party-1"), std::runtime_error);
    EXPECT_THROW(client.toggle_ready("party-1"), std::runtime_error);
    EXPECT_THROW(client.enqueue("party-1", "ranked", 2), std::runtime_error);
    EXPECT_THROW(client.cancel_queue("party-1"), std::runtime_error);
}

TEST(ClientTest, WebSocketNotConnectedByDefault) {
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_FALSE(client.is_ws_connected());
}

// Connecting to a server that is not there must report failure rather than
// silently leaving a socket that never delivers events.
TEST(ClientTest, ConnectWsThrowsWithoutServer) {
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_THROW(client.connect_ws("party-1"), std::runtime_error);
    EXPECT_FALSE(client.is_ws_connected());
}

TEST(ClientTest, DisconnectWsIsSafeWhenNeverConnected) {
    game::Client client("http://localhost:8080", "test_token");
    EXPECT_NO_THROW(client.disconnect_ws());
}

TEST(ClientTest, CanSetCallbacks) {
    game::Client client("http://localhost:8080", "test_token");

    EXPECT_NO_THROW(client.on_match_found([](const game::MatchInfo&) {}));
    EXPECT_NO_THROW(client.on_lobby_update([](const game::LobbyEvent&) {}));
    EXPECT_NO_THROW(client.on_event([](const game::Event&) {}));
}
