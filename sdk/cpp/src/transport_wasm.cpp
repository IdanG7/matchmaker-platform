// Browser transport: emscripten's fetch API for HTTP, websocket.js for
// WebSocket. Used only for Emscripten builds; see transport.hpp.
//
// Both calls below look blocking, which is what keeps one SDK API across
// native and web. A browser cannot actually block the main thread, so this
// relies on -sASYNCIFY: emscripten_sleep() unwinds the C++ stack, lets the
// browser run its event loop, and rewinds when the wait is over. Every
// waiting loop here therefore has to call emscripten_sleep() rather than spin,
// or the callback it is waiting on can never fire and the page hangs.
//
// This costs binary size and some speed, and it is the reason the WASM client
// must be linked with -sASYNCIFY and -lwebsocket.js.

#include "transport.hpp"

#include <emscripten/emscripten.h>
#include <emscripten/fetch.h>
#include <emscripten/websocket.h>

#include <chrono>
#include <cstring>
#include <string>
#include <vector>

namespace game {
namespace detail {
namespace {

// Milliseconds yielded per wait iteration. Small enough to stay responsive,
// large enough not to thrash the Asyncify unwind/rewind machinery.
constexpr int kPollIntervalMs = 10;

struct FetchState {
    bool done = false;
    HttpResponse response;
};

// Handles both outcomes. emscripten routes any non-2xx to onerror, but those
// still carry the API's error detail in the body and must be reported as a
// response rather than a transport failure. A status of 0 means the request
// never reached anyone: DNS failure, refused connection, or a CORS rejection,
// which the browser deliberately does not distinguish.
void on_fetch_done(emscripten_fetch_t* fetch) {
    auto* state = static_cast<FetchState*>(fetch->userData);

    if (fetch->status == 0) {
        state->response.transport_ok = false;
        // Same wording as the native transport, which callers match on.
        state->response.error = "Connection failed";
    } else {
        state->response.transport_ok = true;
        state->response.status = fetch->status;
        if (fetch->numBytes > 0 && fetch->data) {
            state->response.body.assign(fetch->data,
                                        static_cast<size_t>(fetch->numBytes));
        }
    }

    state->done = true;
    emscripten_fetch_close(fetch);
}

} // namespace

HttpResponse http_request(const std::string& base_url,
                          const std::string& method,
                          const std::string& path,
                          const std::string& body,
                          const Headers& headers,
                          int timeout_seconds) {
    FetchState state;

    emscripten_fetch_attr_t attr;
    emscripten_fetch_attr_init(&attr);

    std::strncpy(attr.requestMethod, method.c_str(), sizeof(attr.requestMethod) - 1);
    attr.requestMethod[sizeof(attr.requestMethod) - 1] = '\0';

    attr.attributes = EMSCRIPTEN_FETCH_LOAD_TO_MEMORY;
    attr.onsuccess = on_fetch_done;
    attr.onerror = on_fetch_done;
    attr.userData = &state;
    attr.timeoutMSecs = static_cast<unsigned long>(timeout_seconds) * 1000UL;

    if (!body.empty()) {
        attr.requestData = body.c_str();
        attr.requestDataSize = body.size();
    }

    // emscripten wants a flat array of "Name", "Value", ..., nullptr.
    std::vector<std::string> storage;
    storage.reserve(headers.size() * 2);
    for (const auto& [name, value] : headers) {
        storage.push_back(name);
        storage.push_back(value);
    }
    std::vector<const char*> header_ptrs;
    header_ptrs.reserve(storage.size() + 1);
    for (const auto& entry : storage) header_ptrs.push_back(entry.c_str());
    header_ptrs.push_back(nullptr);
    if (!headers.empty()) {
        attr.requestHeaders = header_ptrs.data();
    }

    const std::string url = base_url + path;
    emscripten_fetch_t* fetch = emscripten_fetch(&attr, url.c_str());
    if (!fetch) {
        HttpResponse failed;
        failed.error = "Could not start the request";
        return failed;
    }

    // Yield to the browser until a callback lands. Asyncify makes this a real
    // suspend rather than a busy wait.
    const int deadline_ms = (timeout_seconds + 5) * 1000;
    int waited_ms = 0;
    while (!state.done && waited_ms < deadline_ms) {
        emscripten_sleep(kPollIntervalMs);
        waited_ms += kPollIntervalMs;
    }

    if (!state.done) {
        HttpResponse failed;
        failed.error = "Request timed out";
        return failed;
    }
    return state.response;
}

// --- WebSocket -------------------------------------------------------------

// The emscripten callbacks are static members rather than free functions so
// they can reach Impl, which the header declares private.
struct WebSocket::Impl {
    EMSCRIPTEN_WEBSOCKET_T socket = 0;
    bool connected = false;
    bool open_failed = false;
    MessageHandler handler;

    static EM_BOOL on_open(int, const EmscriptenWebSocketOpenEvent*, void* user_data) {
        static_cast<Impl*>(user_data)->connected = true;
        return EM_TRUE;
    }

    static EM_BOOL on_close(int, const EmscriptenWebSocketCloseEvent*, void* user_data) {
        static_cast<Impl*>(user_data)->connected = false;
        return EM_TRUE;
    }

    static EM_BOOL on_error(int, const EmscriptenWebSocketErrorEvent*, void* user_data) {
        auto* impl = static_cast<Impl*>(user_data);
        impl->connected = false;
        impl->open_failed = true;
        return EM_TRUE;
    }

    // Buffers the frame. Deliberately does not call the handler.
    //
    // This runs from the browser's event loop, which means it can run while
    // the program is suspended inside emscripten_sleep() waiting on an HTTP
    // response -- entering the queue is exactly such a moment, and the
    // match.found frame answering it arrives milliseconds later. Calling
    // application code from here re-enters WebAssembly mid-unwind, and
    // Asyncify's state machine traps on that: the module dies with
    // "unreachable", which -sASSERTIONS blames on ASYNCIFY_STACK_SIZE and
    // raising that does not help. Copying bytes is safe because this function
    // reaches nothing that can suspend; poll() does the dispatching later.
    static EM_BOOL on_message(int, const EmscriptenWebSocketMessageEvent* event,
                              void* user_data) {
        auto* impl = static_cast<Impl*>(user_data);
        if (!event->isText) return EM_TRUE;

        // numBytes includes the terminating NUL for text frames.
        const size_t length = event->numBytes > 0 ? event->numBytes - 1 : 0;
        impl->pending.emplace_back(reinterpret_cast<const char*>(event->data), length);
        return EM_TRUE;
    }

    std::vector<std::string> pending;
};

WebSocket::WebSocket() : impl_(std::make_unique<Impl>()) {}

WebSocket::~WebSocket() {
    disconnect();
}

void WebSocket::set_message_handler(MessageHandler handler) {
    impl_->handler = std::move(handler);
}

void WebSocket::poll() {
    if (impl_->pending.empty() || !impl_->handler) return;

    // Swapped out first: a handler may make blocking calls of its own, which
    // yield to the browser, which can deliver more frames into the buffer
    // while this loop is still running.
    std::vector<std::string> frames;
    frames.swap(impl_->pending);
    for (const auto& frame : frames) {
        impl_->handler(frame);
    }
}

bool WebSocket::connect(const std::string& url, std::chrono::seconds timeout) {
    if (!emscripten_websocket_is_supported()) {
        return false;
    }

    EmscriptenWebSocketCreateAttributes attr;
    emscripten_websocket_init_create_attributes(&attr);
    attr.url = url.c_str();

    impl_->open_failed = false;
    impl_->socket = emscripten_websocket_new(&attr);
    if (impl_->socket <= 0) {
        return false;
    }

    emscripten_websocket_set_onopen_callback(impl_->socket, impl_.get(), Impl::on_open);
    emscripten_websocket_set_onclose_callback(impl_->socket, impl_.get(), Impl::on_close);
    emscripten_websocket_set_onerror_callback(impl_->socket, impl_.get(), Impl::on_error);
    emscripten_websocket_set_onmessage_callback(impl_->socket, impl_.get(), Impl::on_message);

    const int deadline_ms = static_cast<int>(timeout.count()) * 1000;
    int waited_ms = 0;
    while (!impl_->connected && !impl_->open_failed && waited_ms < deadline_ms) {
        emscripten_sleep(kPollIntervalMs);
        waited_ms += kPollIntervalMs;
    }

    if (!impl_->connected) {
        disconnect();
        return false;
    }
    return true;
}

void WebSocket::disconnect() {
    if (impl_->socket > 0) {
        emscripten_websocket_close(impl_->socket, 1000, "client closing");
        emscripten_websocket_delete(impl_->socket);
        impl_->socket = 0;
    }
    impl_->connected = false;
}

bool WebSocket::is_connected() const {
    return impl_->connected;
}

} // namespace detail
} // namespace game
