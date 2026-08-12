// Native transport: cpp-httplib for HTTP, IXWebSocket for WebSocket.
//
// The browser build uses transport_wasm.cpp instead; see transport.hpp.

#include "transport.hpp"
#include "url.hpp"

#include <httplib.h>
#include <ixwebsocket/IXWebSocket.h>

#include <atomic>
#include <condition_variable>
#include <mutex>

namespace game {
namespace detail {

HttpResponse http_request(const std::string& base_url,
                          const std::string& method,
                          const std::string& path,
                          const std::string& body,
                          const Headers& headers,
                          int timeout_seconds) {
    HttpResponse response;

    const ParsedURL parsed = parse_url(base_url);
    httplib::Client client(parsed.host, parsed.port);
    client.set_connection_timeout(5, 0);
    client.set_read_timeout(timeout_seconds, 0);

    httplib::Headers http_headers;
    for (const auto& [name, value] : headers) {
        http_headers.emplace(name, value);
    }

    httplib::Result res(nullptr, httplib::Error::Unknown);
    if (method == "GET") {
        res = client.Get(path.c_str(), http_headers);
    } else if (method == "POST") {
        res = client.Post(path.c_str(), http_headers, body, "application/json");
    } else if (method == "PATCH") {
        res = client.Patch(path.c_str(), http_headers, body, "application/json");
    } else if (method == "DELETE") {
        res = client.Delete(path.c_str(), http_headers);
    } else {
        response.error = "Unsupported HTTP method: " + method;
        return response;
    }

    if (!res) {
        response.error = "Connection failed";
        return response;
    }

    response.transport_ok = true;
    response.status = res->status;
    response.body = res->body;
    return response;
}

// --- WebSocket -------------------------------------------------------------

struct WebSocket::Impl {
    ix::WebSocket socket;
    std::atomic<bool> connected{false};
    MessageHandler handler;
    std::mutex handler_mutex;
    std::mutex state_mutex;
    std::condition_variable state_cv;

    void set_connected(bool value) {
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            connected = value;
        }
        state_cv.notify_all();
    }
};

WebSocket::WebSocket() : impl_(std::make_unique<Impl>()) {
    impl_->socket.setOnMessageCallback([this](const ix::WebSocketMessagePtr& msg) {
        switch (msg->type) {
        case ix::WebSocketMessageType::Open:
            impl_->set_connected(true);
            break;
        case ix::WebSocketMessageType::Close:
        case ix::WebSocketMessageType::Error:
            impl_->set_connected(false);
            break;
        case ix::WebSocketMessageType::Message: {
            MessageHandler handler;
            {
                std::lock_guard<std::mutex> lock(impl_->handler_mutex);
                handler = impl_->handler;
            }
            if (handler) handler(msg->str);
            break;
        }
        default:
            break;
        }
    });
}

WebSocket::~WebSocket() {
    disconnect();
}

// Frames are dispatched from IXWebSocket's own thread as they arrive, so
// there is nothing buffered for this to hand over. It exists so that callers
// can be written once against both transports.
void WebSocket::poll() {}

void WebSocket::set_message_handler(MessageHandler handler) {
    std::lock_guard<std::mutex> lock(impl_->handler_mutex);
    impl_->handler = std::move(handler);
}

bool WebSocket::connect(const std::string& url, std::chrono::seconds timeout) {
    impl_->socket.setUrl(url);
    impl_->socket.start();

    std::unique_lock<std::mutex> lock(impl_->state_mutex);
    impl_->state_cv.wait_for(lock, timeout, [this] { return impl_->connected.load(); });
    return impl_->connected.load();
}

void WebSocket::disconnect() {
    impl_->socket.stop();
    impl_->set_connected(false);
}

bool WebSocket::is_connected() const {
    return impl_->connected.load();
}

} // namespace detail
} // namespace game
