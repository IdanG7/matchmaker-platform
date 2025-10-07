#include "matchmaker/matchmaker_client.hpp"
#include <algorithm>

namespace matchmaker {

MatchmakerClient::MatchmakerClient(
    const std::string& api_base_url,
    const std::string& ws_base_url
)
    : api_base_url_(api_base_url),
      ws_base_url_(ws_base_url.empty() ? derive_ws_url(api_base_url) : ws_base_url)
{
    // Create HTTP client
    http_client_ = std::make_shared<HTTPClient>(api_base_url_);

    // Create WebSocket client
    ws_client_ = std::make_unique<WebSocketClient>(ws_base_url_, event_queue_);

    // Create API wrappers
    auth_api_ = std::make_unique<AuthAPI>(http_client_);
    profile_api_ = std::make_unique<ProfileAPI>(http_client_);
    party_api_ = std::make_unique<PartyAPI>(http_client_);
    session_api_ = std::make_unique<SessionAPI>(http_client_);
}

MatchmakerClient::~MatchmakerClient() {
    disconnect_websocket();
}

void MatchmakerClient::set_auth_token(const std::string& token) {
    http_client_->set_auth_token(token);
}

void MatchmakerClient::clear_auth_token() {
    http_client_->clear_auth_token();
}

bool MatchmakerClient::connect_websocket(const std::string& party_id) {
    // Need to get current auth token from HTTP client
    // For now, we'll require the user to pass it separately
    // TODO: Store auth token in MatchmakerClient for reuse
    return false;  // Placeholder - needs auth token
}

void MatchmakerClient::disconnect_websocket() {
    if (ws_client_) {
        ws_client_->disconnect();
    }
}

bool MatchmakerClient::is_websocket_connected() const {
    return ws_client_ && ws_client_->is_connected();
}

void MatchmakerClient::on_event(EventType type, EventCallback callback) {
    event_queue_.on(type, std::move(callback));
}

std::optional<Event> MatchmakerClient::poll_event() {
    return event_queue_.poll();
}

Event MatchmakerClient::wait_event() {
    return event_queue_.wait();
}

void MatchmakerClient::process_events(int duration_ms) {
    auto start = std::chrono::steady_clock::now();

    while (true) {
        auto timeout = duration_ms > 0 ?
            std::chrono::milliseconds(duration_ms) :
            std::chrono::milliseconds(0);

        auto event_opt = event_queue_.wait_for(timeout);

        if (!event_opt) {
            break;  // No more events or timeout
        }

        // Event callbacks are already dispatched in wait_for

        if (duration_ms > 0) {
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - start
            ).count();

            if (elapsed >= duration_ms) {
                break;
            }
        }
    }
}

void MatchmakerClient::set_timeout(int seconds) {
    http_client_->set_timeout(seconds);
}

std::string MatchmakerClient::derive_ws_url(const std::string& api_url) {
    std::string ws_url = api_url;

    // Replace http:// with ws:// and https:// with wss://
    if (ws_url.find("https://") == 0) {
        ws_url.replace(0, 8, "wss://");
    } else if (ws_url.find("http://") == 0) {
        ws_url.replace(0, 7, "ws://");
    }

    return ws_url;
}

} // namespace matchmaker
