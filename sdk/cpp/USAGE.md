# C++ SDK Usage Guide

This guide shows how to integrate the Multiplayer Matchmaking SDK into your game.

## Installation

### Option 1: Download Pre-built Binaries (Easiest)

Download the latest release from [GitHub Releases](https://github.com/IdanG7/matchmaker-platform/releases):

**Linux:**
```bash
# Download and extract
wget https://github.com/IdanG7/matchmaker-platform/releases/latest/download/game-sdk-linux-x64.tar.gz
tar -xzf game-sdk-linux-x64.tar.gz
```

**macOS:**
```bash
# Download and extract
curl -L https://github.com/IdanG7/matchmaker-platform/releases/latest/download/game-sdk-macos-x64.tar.gz -o game-sdk-macos-x64.tar.gz
tar -xzf game-sdk-macos-x64.tar.gz
```

Then in your `CMakeLists.txt`:
```cmake
# Add SDK include directory
include_directories(/path/to/game-sdk-v0.1.1-<platform>/include)

# Link against the SDK library
target_link_libraries(your_game PRIVATE
    /path/to/game-sdk-v0.1.1-<platform>/libgame-sdk.a
    ssl crypto z pthread  # Required dependencies
)
```

**Dependencies:**
- Ubuntu/Debian: `sudo apt-get install libssl-dev zlib1g-dev`
- macOS: `brew install openssl` (zlib included)

### Option 2: CMake FetchContent (Recommended for CI/CD)

Add to your `CMakeLists.txt`:

```cmake
include(FetchContent)

FetchContent_Declare(
    game-sdk
    GIT_REPOSITORY https://github.com/IdanG7/matchmaker-platform.git
    GIT_TAG v0.1.1  # Use specific version tag
    SOURCE_SUBDIR sdk/cpp
)

FetchContent_MakeAvailable(game-sdk)

# Link to your game executable
target_link_libraries(your_game PRIVATE game-sdk)
```

### Option 3: Manual Build

```bash
git clone https://github.com/IdanG7/matchmaker-platform.git
cd matchmaker-platform/sdk/cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
cmake --install build --prefix /usr/local
```

Then link in your project:
```cmake
find_package(game-sdk REQUIRED)
target_link_libraries(your_game PRIVATE game-sdk)
```

## Upgrading from 0.1.16

0.1.17 changes the public API. Most of the party and matchmaking surface in
0.1.16 could not have worked: it called endpoints the server does not serve and
read JSON fields the server does not send, so those calls failed at runtime or
returned empty values. Fixing them meant changing signatures.

| 0.1.16 | 0.1.17 | Why |
|---|---|---|
| `SDK::authenticate(email, password)` | `SDK::login(username, password)` | The old one returned "Not implemented". Login takes a username, not an email. |
| — | `SDK::register_user(...)` | Registering through the SDK stores the token for you. |
| `Client::ready()` | `Client::set_ready(party_id, bool)` | The old call had no party id and hit a path that does not exist. Prefer `set_ready` over `toggle_ready`: creating a party already readies you. |
| `Party::member_ids` | `Party::members` | The server sends member objects under `members`; the old field was always empty. |
| `MatchInfo::token` | `MatchInfo::server_token` | The server names it `server_token`; the old field was always empty. |
| `on_lobby_update(Party)` | `on_lobby_update(LobbyEvent)` | These events are deltas, not snapshots. The old callback handed you a `Party` with only an id filled in. |
| `Client::join_party` returns `void` | returns `Party` | Saves an immediate follow-up fetch. |

Also new: `Client::get_party`, `MatchInfo::server_url` and
`MatchInfo::split_endpoint`, `Profile::party_id` (so a reconnecting client can
recover a party it is still in), and `game::Session` for reporting match
results from a game server.

The SDK now builds for WebAssembly as well as native, with the same API on
both. See [Browser builds](#browser-builds).

## Browser builds

The SDK compiles under Emscripten, using the browser's fetch and WebSocket
rather than sockets. The API is identical, including its blocking calls, which
work because the WASM build links `-sASYNCIFY`.

```bash
emcmake cmake -S sdk/cpp -B build-wasm
cmake --build build-wasm
```

Linking the library brings `-sASYNCIFY`, `-sFETCH=1` and `-lwebsocket.js` with
it. Two things to keep in mind:

- A page served over https cannot open a `ws://` socket or call an `http://`
  API. Serve the backend over TLS, and use `MatchInfo::server_url`, which is
  set when the game servers sit behind a proxy.
- Asyncify suspends the calling stack. Calling a blocking SDK method from
  inside an `emscripten_set_main_loop` callback works, but it yields mid-frame,
  so do it from a menu or loading state rather than every frame.

## Quick Start

### 1. Authentication

```cpp
#include <game/sdk.hpp>
#include <iostream>

int main() {
    const std::string API_URL = "https://your-game-backend.com";

    game::SDK sdk(API_URL);

    // Registering or logging in stores the token on the SDK, so client()
    // is authenticated from here on. Neither throws; check success.
    auto result = sdk.register_user(
        "player@example.com",
        "PlayerName",
        "secure_password",
        "us-west"
    );

    if (!result.success) {
        // Already registered? Log in instead.
        result = sdk.login("PlayerName", "secure_password");
    }

    if (!result.success) {
        std::cerr << "Sign-in failed: " << result.error << std::endl;
        return 1;
    }

    return 0;
}
```

### 2. Get Player Profile

```cpp
// Get profile
auto profile = sdk.client().get_profile();
std::cout << "Username: " << profile.username << std::endl;
std::cout << "Region: " << profile.region << std::endl;
std::cout << "MMR: " << profile.mmr << std::endl;

// Update profile
profile.region = "eu-west";
sdk.client().update_profile(profile);
```

### 3. Create and Join Parties

```cpp
// Player 1: Create a party
auto party = sdk.client().create_party();
std::cout << "Party ID: " << party.id << std::endl;

// Share party.id with Player 2 (e.g., via friend invite)

// Player 2: Join the party. Returns the updated party.
auto joined = sdk2.client().join_party(party.id);
std::cout << joined.members.size() << " members" << std::endl;

// Mark players ready.
//
// Use set_ready rather than toggle_ready: whoever creates a party is
// already ready, so toggling right after create_party un-readies them and
// the queue then refuses the party.
sdk.client().set_ready(party.id, true);
sdk2.client().set_ready(party.id, true);
```

### 4. Real-time Party Updates with WebSocket

```cpp
#include <game/sdk.hpp>
#include <iostream>

int main() {
    game::SDK sdk(API_URL);
    sdk.set_token(access_token);

    // Lobby events describe what changed rather than carrying the whole
    // party, because that is what the server sends. Call get_party() when
    // you need the full state.
    sdk.client().on_lobby_update([&sdk](const game::LobbyEvent& ev) {
        switch (ev.change) {
        case game::LobbyChange::MemberJoined:
            std::cout << ev.username << " joined" << std::endl;
            break;
        case game::LobbyChange::MemberReady:
            std::cout << ev.username << (ev.ready ? " is ready" : " is not ready")
                      << std::endl;
            break;
        case game::LobbyChange::QueueEntered:
            std::cout << "Queued for " << ev.mode << std::endl;
            break;
        default:
            break;
        }
    });

    sdk.client().on_match_found([](const game::MatchInfo& match) {
        std::cout << "Match found!" << std::endl;
        std::cout << "  Match ID: " << match.match_id << std::endl;
        std::cout << "  Server:   " << match.server_endpoint << std::endl;
        std::cout << "  Token:    " << match.server_token << std::endl;

        // server_url is set when the servers sit behind a proxy, and is
        // required in a browser. Fall back to host:port when it is empty.
        std::string host;
        uint16_t port = 0;
        if (!match.server_url.empty()) {
            // connect to match.server_url
        } else if (match.split_endpoint(host, port)) {
            // connect to host:port
        }
    });

    // Create party
    auto party = sdk.client().create_party();

    // Connect to WebSocket for real-time updates
    sdk.client().connect_ws(party.id);

    // Keep program running to receive events
    std::cout << "Waiting for events... (Ctrl+C to exit)" << std::endl;
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}
```

### 5. Matchmaking Queue

```cpp
// Enter matchmaking queue
try {
    sdk.client().enqueue(party.id, "ranked", 5); // 5v5 ranked match
    std::cout << "Queued for matchmaking!" << std::endl;
} catch (const std::exception& e) {
    std::cerr << "Queue failed: " << e.what() << std::endl;
}

// When match is found, the on_match_found callback will be triggered

// Cancel queue if needed
sdk.client().cancel_queue(party.id);
```

## Complete Example: Game Client

```cpp
#include <game/sdk.hpp>
#include <iostream>
#include <thread>
#include <chrono>

class GameClient {
public:
    GameClient(const std::string& api_url)
        : sdk_(api_url), in_match_(false) {}

    bool login(const std::string& username, const std::string& password) {
        // Note this takes a username, not an email address.
        auto result = sdk_.login(username, password);
        if (!result.success) {
            std::cerr << "Login failed: " << result.error << std::endl;
            return false;
        }

        setupCallbacks();
        return true;
    }

    void createPartyAndQueue() {
        // Create party
        party_ = sdk_.client().create_party();
        std::cout << "Party created: " << party_.id << std::endl;

        // Connect WebSocket
        sdk_.client().connect_ws(party_.id);

        // Mark ready
        sdk_.client().set_ready(party_.id, true);

        // Enter queue
        sdk_.client().enqueue(party_.id, "casual", 5);
        std::cout << "Searching for match..." << std::endl;
    }

    void waitForMatch() {
        while (!in_match_) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

private:
    void setupCallbacks() {
        sdk_.client().on_lobby_update([this](const game::LobbyEvent& ev) {
            std::cout << "Party update: " << ev.username << std::endl;
        });

        sdk_.client().on_match_found([this](const game::MatchInfo& match) {
            std::cout << "\n=== MATCH FOUND ===" << std::endl;
            std::cout << "Server: " << match.server_endpoint << std::endl;
            std::cout << "Match ID: " << match.match_id << std::endl;

            // TODO: Connect to game server
            connectToGameServer(match);
            in_match_ = true;
        });
    }

    void connectToGameServer(const game::MatchInfo& match) {
        // Your game networking code here
        std::cout << "Connecting to game server..." << std::endl;
    }

    std::string api_url_;
    game::SDK sdk_;
    game::Party party_;
    bool in_match_;
};

int main() {
    GameClient client("https://your-backend.com");

    if (!client.login("PlayerName", "password")) {
        return 1;
    }

    client.createPartyAndQueue();
    client.waitForMatch();

    return 0;
}
```

## Error Handling

The SDK uses exceptions for errors:

```cpp
try {
    auto profile = sdk.client().get_profile();
} catch (const std::runtime_error& e) {
    std::cerr << "Error: " << e.what() << std::endl;
    // Handle error (e.g., retry, show error to user)
}
```

Auth functions return `AuthResult` with error messages:

```cpp
auto result = game::Auth::login(url, username, password);
if (!result.success) {
    std::cerr << "Login failed: " << result.error << std::endl;
}
```

## Thread Safety

- Callback registration is mutex-guarded, and each request uses its own
  connection
- Natively, WebSocket callbacks are invoked on a background thread. Under
  Emscripten there are no threads and they run on the browser's event loop
- Either way the callback does not run on your game loop, so marshal work
  across rather than touching game state directly:

```cpp
std::mutex match_mutex;
game::MatchInfo current_match;

sdk.client().on_match_found([&](const game::MatchInfo& match) {
    std::lock_guard<std::mutex> lock(match_mutex);
    current_match = match;
});
```

## API Reference

See the header files for complete API documentation:
- `include/game/sdk.hpp` - Main SDK class
- `include/game/auth.hpp` - Authentication functions
- `include/game/client.hpp` - Client operations
- `include/game/session.hpp` - Match result reporting, for game servers
- `include/game/types.hpp` - Data types and structures

## Examples

Full working examples are in `examples/`:
- `simple_client.cpp` - the whole flow: sign in, party, queue, match found
- `party_test.cpp` - two-player party test that exits non-zero on failure,
  which is what catches drift between the SDK and the server

Build and run:
```bash
cd build
./examples/party_test
```

## Troubleshooting

### Connection Failures

If you get "Connection failed" errors:
1. Check that the backend API is running
2. Verify the URL is correct (http://localhost:8080 for local dev)
3. Check firewall settings

### WebSocket Not Connecting

1. Make sure you're connected to a party first
2. Verify the party ID is correct
3. Check that your token is valid (not expired)

### Build Issues

If CMake can't find dependencies:
```bash
# Clean build directory
rm -rf build
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/IdanG7/matchmaker-platform/issues
- Documentation: See `README.md` in the repository root
