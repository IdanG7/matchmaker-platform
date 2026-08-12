#pragma once

// Internal transport layer. Not part of the installed public headers.
//
// The SDK's public API is blocking, and it stays that way in the browser: the
// WASM build is compiled with -sASYNCIFY, which lets these calls yield to the
// browser's event loop and resume, so one API serves both targets. Two
// implementations satisfy this interface:
//
//   transport_native.cpp  cpp-httplib + IXWebSocket, real sockets and threads
//   transport_wasm.cpp    emscripten fetch + websocket.js, no threads at all
//
// Everything above this line is shared.

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace game {
namespace detail {

using Headers = std::vector<std::pair<std::string, std::string>>;

struct HttpResponse {
    // Whether a response was received at all. A 404 is transport_ok with
    // status 404; an unreachable host is transport_ok = false.
    bool transport_ok = false;
    int status = 0;
    std::string body;
    std::string error;  // set when transport_ok is false
};

// Performs a blocking HTTP request. base_url carries scheme, host and port.
HttpResponse http_request(const std::string& base_url,
                          const std::string& method,
                          const std::string& path,
                          const std::string& body,
                          const Headers& headers,
                          int timeout_seconds = 10);

// A WebSocket that delivers text frames to a handler.
//
// Natively the handler runs on the socket's own thread. Under Emscripten it
// runs from poll(), which the owner must call. Either way the handler arrives
// from somewhere other than the call that is running, so callers treat it as
// asynchronous on both targets.
class WebSocket {
public:
    using MessageHandler = std::function<void(const std::string&)>;

    WebSocket();
    ~WebSocket();

    WebSocket(const WebSocket&) = delete;
    WebSocket& operator=(const WebSocket&) = delete;

    // Set before connecting so no early frame is missed.
    void set_message_handler(MessageHandler handler);

    // Delivers whatever frames have arrived since the last call.
    //
    // Native builds dispatch from the socket thread and this does nothing.
    // Under Emscripten it is the only thing that dispatches, and it must be
    // called from ordinary program flow -- a game loop -- and never from
    // inside a blocking SDK call. A browser frame can land while a request is
    // suspended mid-Asyncify-unwind, and running application code at that
    // moment traps the whole module on an "unreachable". Buffering the frame
    // and handing it over later is what keeps that from happening.
    void poll();

    // Blocks until the socket opens or the timeout expires. Returns whether
    // it opened, so a caller can report failure rather than sit on a socket
    // that will never deliver anything.
    bool connect(const std::string& url, std::chrono::seconds timeout);

    void disconnect();
    bool is_connected() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace detail
} // namespace game
