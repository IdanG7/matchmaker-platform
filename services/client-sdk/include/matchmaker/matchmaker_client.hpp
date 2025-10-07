#pragma once

#include "types.hpp"
#include "http_client.hpp"
#include "websocket_client.hpp"
#include "event_queue.hpp"
#include "auth_api.hpp"
#include "profile_api.hpp"
#include "party_api.hpp"
#include "session_api.hpp"
#include <memory>
#include <string>

namespace matchmaker {

/**
 * Main client SDK class.
 * Provides a unified interface to all matchmaking platform features.
 *
 * Example usage:
 *   MatchmakerClient client("http://localhost:8080");
 *   auto result = client.auth().register_user({...});
 *   if (result) {
 *       client.set_auth_token(result.value.access_token);
 *       auto party = client.party().create_party(5);
 *       client.connect_websocket(party.value.party_id);
 *       client.on_event(EventType::MATCH_FOUND, [](const Event& e) {
 *           // Handle match found
 *       });
 *   }
 */
class MatchmakerClient {
public:
    /**
     * Create a new client instance.
     *
     * @param api_base_url Base URL of the API server (e.g., "http://localhost:8080")
     * @param ws_base_url Base URL for WebSocket connections (e.g., "ws://localhost:8080")
     *                    If empty, derives from api_base_url by replacing http with ws
     */
    explicit MatchmakerClient(
        const std::string& api_base_url,
        const std::string& ws_base_url = ""
    );

    ~MatchmakerClient();

    // ========================================================================
    // API Access
    // ========================================================================

    /**
     * Get authentication API.
     */
    AuthAPI& auth() { return *auth_api_; }

    /**
     * Get profile API.
     */
    ProfileAPI& profile() { return *profile_api_; }

    /**
     * Get party/lobby API.
     */
    PartyAPI& party() { return *party_api_; }

    /**
     * Get session API.
     */
    SessionAPI& session() { return *session_api_; }

    // ========================================================================
    // Authentication
    // ========================================================================

    /**
     * Set authentication token for subsequent API calls.
     *
     * @param token Access token from login or registration
     */
    void set_auth_token(const std::string& token);

    /**
     * Clear authentication token.
     */
    void clear_auth_token();

    // ========================================================================
    // WebSocket
    // ========================================================================

    /**
     * Connect to party WebSocket for real-time updates.
     *
     * @param party_id Party ID to connect to
     * @return True on success, false on failure
     */
    bool connect_websocket(const std::string& party_id);

    /**
     * Disconnect from party WebSocket.
     */
    void disconnect_websocket();

    /**
     * Check if WebSocket is connected.
     */
    bool is_websocket_connected() const;

    // ========================================================================
    // Event Handling
    // ========================================================================

    /**
     * Register callback for specific event type.
     *
     * @param type Event type to listen for
     * @param callback Function to call when event occurs
     */
    void on_event(EventType type, EventCallback callback);

    /**
     * Poll for next event (non-blocking).
     *
     * @return Event if available, nullopt otherwise
     */
    std::optional<Event> poll_event();

    /**
     * Wait for next event (blocking).
     *
     * @return Next event from queue
     */
    Event wait_event();

    /**
     * Process events for a duration (useful for game loop integration).
     * Calls registered callbacks for any pending events.
     *
     * @param duration_ms Time to process events (0 = process all pending)
     */
    void process_events(int duration_ms = 0);

    // ========================================================================
    // Configuration
    // ========================================================================

    /**
     * Set HTTP request timeout.
     *
     * @param seconds Timeout in seconds (default: 30)
     */
    void set_timeout(int seconds);

private:
    std::string api_base_url_;
    std::string ws_base_url_;

    // Core components
    std::shared_ptr<HTTPClient> http_client_;
    EventQueue event_queue_;
    std::unique_ptr<WebSocketClient> ws_client_;

    // API wrappers
    std::unique_ptr<AuthAPI> auth_api_;
    std::unique_ptr<ProfileAPI> profile_api_;
    std::unique_ptr<PartyAPI> party_api_;
    std::unique_ptr<SessionAPI> session_api_;

    std::string derive_ws_url(const std::string& api_url);
};

} // namespace matchmaker
