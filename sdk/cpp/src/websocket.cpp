#include <ixwebsocket/IXWebSocket.h>
#include <nlohmann/json.hpp>
#include <string>
#include <functional>
#include <mutex>
#include <thread>
#include <queue>

using json = nlohmann::json;

namespace game {
namespace websocket {

using EventCallback = std::function<void(const std::string& event, const json& data)>;

class WebSocketClient {
public:
    WebSocketClient(const std::string& url, const std::string& token)
        : url_(url), token_(token), connected_(false) {

        // Build WebSocket URL with token as query parameter
        std::string ws_url = url;

        // Convert http:// to ws://
        if (ws_url.find("http://") == 0) {
            ws_url = "ws://" + ws_url.substr(7);
        } else if (ws_url.find("https://") == 0) {
            ws_url = "wss://" + ws_url.substr(8);
        }

        // Add token query parameter
        ws_url += "?token=" + token;

        ws_.setUrl(ws_url);

        // Set up event handlers
        ws_.setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
            this->onMessage(msg);
        });
    }

    ~WebSocketClient() {
        disconnect();
    }

    void connect() {
        ws_.start();

        // Wait a bit for connection (simple approach)
        for (int i = 0; i < 50; i++) {
            if (connected_) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

    void disconnect() {
        ws_.stop();
        connected_ = false;
    }

    bool is_connected() const {
        return connected_;
    }

    void send(const std::string& message) {
        ws_.send(message);
    }

    void send_ping() {
        json ping_msg = {
            {"type", "ping"}
        };
        send(ping_msg.dump());
    }

    void set_event_callback(EventCallback callback) {
        std::lock_guard<std::mutex> lock(callback_mutex_);
        event_callback_ = callback;
    }

private:
    void onMessage(const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Open) {
            connected_ = true;
        } else if (msg->type == ix::WebSocketMessageType::Close) {
            connected_ = false;
        } else if (msg->type == ix::WebSocketMessageType::Message) {
            try {
                auto data = json::parse(msg->str);

                std::string event = data.value("event", "unknown");
                json event_data = data.value("data", json::object());

                // Invoke callback
                std::lock_guard<std::mutex> lock(callback_mutex_);
                if (event_callback_) {
                    event_callback_(event, event_data);
                }
            } catch (const std::exception& e) {
                // Ignore parse errors
            }
        } else if (msg->type == ix::WebSocketMessageType::Error) {
            connected_ = false;
        }
    }

    ix::WebSocket ws_;
    std::string url_;
    std::string token_;
    bool connected_;
    EventCallback event_callback_;
    std::mutex callback_mutex_;
};

} // namespace websocket
} // namespace game
