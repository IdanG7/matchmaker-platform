#pragma once

#include "types.hpp"
#include "event_queue.hpp"
#include <ixwebsocket/IXWebSocket.h>
#include <memory>
#include <atomic>
#include <mutex>

namespace matchmaker {

/**
 * WebSocket client for real-time party updates.
 * Thread-safe event delivery via EventQueue.
 */
class WebSocketClient {
public:
    WebSocketClient(const std::string& base_url, EventQueue& event_queue);
    ~WebSocketClient();

    // Connection management
    bool connect(const std::string& party_id, const std::string& auth_token);
    void disconnect();
    bool is_connected() const;

    // Send ping to keep connection alive
    void send_ping();

private:
    std::string base_url_;
    EventQueue& event_queue_;
    std::unique_ptr<ix::WebSocket> ws_;
    std::atomic<bool> connected_{false};
    mutable std::mutex mutex_;

    void setup_callbacks();
    void handle_message(const std::string& message);
    EventType parse_event_type(const std::string& event);
};

} // namespace matchmaker
