# Matchmaker Client SDK (C++)

A modern C++ SDK for interacting with the Multiplayer Matchmaking Platform.

## Features

- ✅ **Easy-to-use API** - Simple, intuitive interface for all matchmaking operations
- ✅ **REST API wrapper** - Type-safe wrappers for authentication, profiles, parties, and sessions
- ✅ **WebSocket support** - Real-time party updates with event callbacks
- ✅ **Thread-safe** - Safe for use in multithreaded game engines
- ✅ **Modern C++17** - Uses modern C++ features and best practices
- ✅ **Cross-platform** - Builds on Linux, macOS, and Windows

## Dependencies

The SDK uses the following libraries (automatically fetched by CMake):

- [cpp-httplib](https://github.com/yhirose/cpp-httplib) - HTTP client
- [IXWebSocket](https://github.com/machinezone/IXWebSocket) - WebSocket client
- [nlohmann/json](https://github.com/nlohmann/json) - JSON parsing

## Building

### Requirements

- CMake 3.15+
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- OpenSSL (for HTTPS/WSS support)

### Build Steps

```bash
cd services/client-sdk
mkdir build && cd build
cmake ..
make
```

### Build Options

```bash
cmake -DBUILD_EXAMPLES=ON -DBUILD_TESTS=ON ..
```

- `BUILD_EXAMPLES` - Build example applications (default: ON)
- `BUILD_TESTS` - Build unit tests (default: ON)

## Quick Start

### Basic Usage

```cpp
#include <matchmaker/matchmaker_client.hpp>

using namespace matchmaker;

int main() {
    // Create client
    MatchmakerClient client("http://localhost:8080");

    // Register user
    RegisterRequest req;
    req.username = "player123";
    req.email = "player@example.com";
    req.password = "secure_password";
    req.region = "us-west";

    auto result = client.auth().register_user(req);
    if (!result) {
        std::cerr << "Error: " << result.error.to_string() << "\n";
        return 1;
    }

    // Set auth token
    client.set_auth_token(result.value.access_token);

    // Get profile
    auto profile = client.profile().get_profile();
    if (profile) {
        std::cout << "MMR: " << profile.value.mmr << "\n";
    }

    return 0;
}
```

### Full Matchmaking Flow

```cpp
#include <matchmaker/matchmaker_client.hpp>

using namespace matchmaker;

int main() {
    MatchmakerClient client("http://localhost:8080");

    // 1. Authenticate
    LoginRequest login{/*.username =*/ "player123", /*.password =*/ "password"};
    auto auth = client.auth().login(login);
    client.set_auth_token(auth.value.access_token);

    // 2. Create party
    auto party = client.party().create_party(5);
    std::string party_id = party.value.party_id;

    // 3. Set up event handlers
    client.on_event(EventType::MATCH_FOUND, [&](const Event& e) {
        std::cout << "Match found!\n";
        std::string match_id = e.data["match_id"];

        // Get session details
        auto session = client.session().get_session(match_id);
        std::cout << "Connect to: " << session.value.server_endpoint << "\n";
    });

    // 4. Set ready and enter queue
    client.party().set_ready(party_id, true);
    client.party().enter_queue(QueueRequest{"ranked", 1});

    // 5. Process events
    while (true) {
        client.process_events(100);  // Process for 100ms
        // Game loop here...
    }

    return 0;
}
```

## API Reference

### Authentication (`client.auth()`)

```cpp
// Register new user
Result<AuthTokens> register_user(const RegisterRequest& request);

// Login
Result<AuthTokens> login(const LoginRequest& request);

// Refresh token
Result<AuthTokens> refresh_token(const std::string& refresh_token);
```

### Profile (`client.profile()`)

```cpp
// Get current user profile
Result<ProfileInfo> get_profile();

// Update profile
Result<ProfileInfo> update_profile(const ProfileUpdateRequest& request);
```

### Party (`client.party()`)

```cpp
// Create party
Result<PartyInfo> create_party(int max_size = 5);

// Join party
Result<PartyInfo> join_party(const std::string& party_id);

// Leave party
Result<void> leave_party(const std::string& party_id);

// Set ready status
Result<PartyInfo> set_ready(const std::string& party_id, bool ready);

// Get party details
Result<PartyInfo> get_party(const std::string& party_id);

// Enter matchmaking queue
Result<void> enter_queue(const QueueRequest& request);

// Leave queue
Result<void> leave_queue();
```

### Session (`client.session()`)

```cpp
// Get session details
Result<SessionInfo> get_session(const std::string& match_id);

// Send heartbeat
Result<void> send_heartbeat(const std::string& match_id);

// Submit match result (game server only)
Result<void> submit_result(const MatchResult& result);
```

### Event Handling

```cpp
// Register event callback
client.on_event(EventType::MATCH_FOUND, [](const Event& e) {
    // Handle event
});

// Poll for events (non-blocking)
if (auto event = client.poll_event()) {
    // Handle event
}

// Wait for event (blocking)
Event event = client.wait_event();

// Process events for duration (useful for game loops)
client.process_events(100);  // Process for 100ms
```

### Event Types

- `CONNECTED` - WebSocket connected
- `DISCONNECTED` - WebSocket disconnected
- `MEMBER_JOINED` - Player joined party
- `MEMBER_LEFT` - Player left party
- `MEMBER_READY` - Player ready status changed
- `PARTY_UPDATED` - Party state changed
- `QUEUE_ENTERED` - Party entered queue
- `QUEUE_LEFT` - Party left queue
- `MATCH_FOUND` - Match has been found

## Error Handling

All API methods return a `Result<T>` type that can be checked for success:

```cpp
auto result = client.auth().login(request);

if (result) {
    // Success
    auto tokens = result.value;
} else {
    // Failure
    std::cerr << "Error: " << result.error.to_string() << "\n";
    std::cerr << "Status: " << result.error.status_code << "\n";
}
```

## Examples

See the `examples/` directory for complete examples:

- `basic_example.cpp` - Registration, login, and profile management
- `full_flow_example.cpp` - Complete matchmaking flow with events

Build and run examples:

```bash
cd build
./examples/basic_example http://localhost:8080
./examples/full_flow_example http://localhost:8080
```

## Integration with Game Engines

### Unreal Engine

```cpp
// In your game instance or subsystem
UMatchmakerSubsystem::Initialize() {
    Client = MakeUnique<matchmaker::MatchmakerClient>("http://localhost:8080");

    // Process events in Tick
    RegisterTickFunction(...);
}

void UMatchmakerSubsystem::Tick(float DeltaTime) {
    Client->process_events(0);  // Process all pending events
}
```

### Unity (C++ plugin)

Create a C wrapper for the SDK and expose it via P/Invoke.

### Custom Engine

```cpp
// In your main loop
void GameLoop() {
    while (running) {
        // Process matchmaker events
        matchmaker_client->process_events(16);  // 16ms = ~60fps

        // Rest of game loop
        ProcessInput();
        Update();
        Render();
    }
}
```

## Thread Safety

- All API methods are thread-safe
- Event queue is thread-safe
- WebSocket callbacks run on background thread
- Use callbacks or poll events from your main thread

## License

See main project LICENSE file.

## Support

For issues and feature requests, see the main project repository.
