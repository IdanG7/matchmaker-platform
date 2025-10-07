#include "matchmaker/websocket_client.hpp"
#include <iostream>

namespace matchmaker {

WebSocketClient::WebSocketClient(const std::string& base_url, EventQueue& event_queue)
    : base_url_(base_url), event_queue_(event_queue) {
    ws_ = std::make_unique<ix::WebSocket>();
}

WebSocketClient::~WebSocketClient() {
    disconnect();
}

bool WebSocketClient::connect(const std::string& party_id, const std::string& auth_token) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (connected_) {
        return true;  // Already connected
    }

    // Construct WebSocket URL with auth token as query parameter
    std::string url = base_url_ + "/v1/ws/party/" + party_id + "?token=" + auth_token;

    ws_->setUrl(url);
    setup_callbacks();

    ws_->start();

    // Wait briefly for connection
    for (int i = 0; i < 50 && !connected_; ++i) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    return connected_.load();
}

void WebSocketClient::disconnect() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (ws_) {
        ws_->stop();
        connected_ = false;
    }
}

bool WebSocketClient::is_connected() const {
    return connected_.load();
}

void WebSocketClient::send_ping() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (ws_ && connected_) {
        json ping_msg = {
            {"type", "ping"}
        };
        ws_->send(ping_msg.dump());
    }
}

void WebSocketClient::setup_callbacks() {
    ws_->setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Message) {
            handle_message(msg->str);
        }
        else if (msg->type == ix::WebSocketMessageType::Open) {
            connected_ = true;

            // Emit connected event
            Event event{
                EventType::CONNECTED,
                {{"message", "Connected to WebSocket"}},
                std::chrono::system_clock::now()
            };
            event_queue_.push(event);
        }
        else if (msg->type == ix::WebSocketMessageType::Close) {
            connected_ = false;

            // Emit disconnected event
            Event event{
                EventType::DISCONNECTED,
                {{"reason", msg->closeInfo.reason}, {"code", msg->closeInfo.code}},
                std::chrono::system_clock::now()
            };
            event_queue_.push(event);
        }
        else if (msg->type == ix::WebSocketMessageType::Error) {
            // Emit error event
            Event event{
                EventType::ERROR,
                {{"error", msg->errorInfo.reason}},
                std::chrono::system_clock::now()
            };
            event_queue_.push(event);
        }
    });
}

void WebSocketClient::handle_message(const std::string& message) {
    try {
        json msg = json::parse(message);

        std::string event_name = msg.value("event", "unknown");
        EventType type = parse_event_type(event_name);

        Event event{
            type,
            msg.contains("data") ? msg["data"] : json::object(),
            std::chrono::system_clock::now()
        };

        event_queue_.push(event);

    } catch (const json::parse_error& e) {
        // Emit error event for invalid JSON
        Event event{
            EventType::ERROR,
            {{"error", "Failed to parse WebSocket message"}, {"message", message}},
            std::chrono::system_clock::now()
        };
        event_queue_.push(event);
    }
}

EventType WebSocketClient::parse_event_type(const std::string& event) {
    if (event == "connected") return EventType::CONNECTED;
    if (event == "member_joined") return EventType::MEMBER_JOINED;
    if (event == "member_left") return EventType::MEMBER_LEFT;
    if (event == "member_ready") return EventType::MEMBER_READY;
    if (event == "party_updated") return EventType::PARTY_UPDATED;
    if (event == "queue_entered") return EventType::QUEUE_ENTERED;
    if (event == "queue_left") return EventType::QUEUE_LEFT;
    if (event == "match_found") return EventType::MATCH_FOUND;
    if (event == "pong") return EventType::CONNECTED;  // Keep-alive response

    return EventType::UNKNOWN;
}

} // namespace matchmaker
