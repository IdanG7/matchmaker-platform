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
include_directories(/path/to/game-sdk-v1.0.0-<platform>/include)

# Link against the SDK library
target_link_libraries(your_game PRIVATE
    /path/to/game-sdk-v1.0.0-<platform>/libgame-sdk.a
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
    GIT_TAG v1.0.0  # Use specific version tag
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

## Quick Start

### 1. Authentication

```cpp
#include <game/sdk.hpp>
#include <iostream>

int main() {
    const std::string API_URL = "https://your-game-backend.com";

    // Register a new user
    auto result = game::Auth::register_user(
        API_URL,
        "player@example.com",
        "PlayerName",
        "secure_password",
        "us-west"
    );

    if (!result.success) {
        std::cerr << "Registration failed: " << result.error << std::endl;
        return 1;
    }

    std::cout << "Logged in! Token: " << result.access_token << std::endl;

    // Create SDK instance
    game::SDK sdk(API_URL);
    sdk.set_token(result.access_token);

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

// Player 2: Join the party
sdk2.client().join_party(party.id);

// Players mark themselves as ready
sdk.client().ready();
sdk2.client().ready();
```

### 4. Real-time Party Updates with WebSocket

```cpp
#include <game/sdk.hpp>
#include <iostream>

int main() {
    game::SDK sdk(API_URL);
    sdk.set_token(access_token);

    // Set up event callbacks
    sdk.client().on_lobby_update([](const game::Party& party) {
        std::cout << "Party updated!" << std::endl;
        std::cout << "  Members: " << party.member_ids.size() << std::endl;
        std::cout << "  Status: " << party.status << std::endl;
    });

    sdk.client().on_match_found([](const game::MatchInfo& match) {
        std::cout << "Match found!" << std::endl;
        std::cout << "  Server: " << match.server_endpoint << std::endl;
        std::cout << "  Match ID: " << match.match_id << std::endl;
        std::cout << "  Token: " << match.token << std::endl;

        // Connect to game server with match.server_endpoint and match.token
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

    bool login(const std::string& email, const std::string& password) {
        auto result = game::Auth::login(api_url_, email, password);
        if (!result.success) {
            std::cerr << "Login failed: " << result.error << std::endl;
            return false;
        }

        sdk_.set_token(result.access_token);
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
        sdk_.client().ready();

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
        sdk_.client().on_lobby_update([this](const game::Party& party) {
            std::cout << "Party update: " << party.member_ids.size()
                      << " members" << std::endl;
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

    if (!client.login("player@example.com", "password")) {
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

- All SDK methods are thread-safe
- WebSocket callbacks are invoked on a background thread
- Use mutexes if modifying shared state in callbacks:

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
- `include/game/types.hpp` - Data types and structures

## Examples

Full working examples are in `examples/`:
- `simple_client.cpp` - Basic SDK usage
- `party_test.cpp` - Two-player party test with WebSocket events

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
