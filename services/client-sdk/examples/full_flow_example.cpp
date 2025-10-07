/**
 * Full flow example demonstrating complete matchmaking flow.
 * Shows registration, party creation, queue entry, and event handling.
 */

#include "matchmaker/matchmaker_client.hpp"
#include <iostream>
#include <string>
#include <thread>
#include <atomic>

using namespace matchmaker;

std::atomic<bool> match_found{false};
std::string found_match_id;

void handle_event(const Event& event) {
    switch (event.type) {
        case EventType::CONNECTED:
            std::cout << "[WS] Connected to party WebSocket\n";
            break;

        case EventType::MEMBER_JOINED:
            std::cout << "[WS] Member joined: "
                      << event.data["username"].get<std::string>() << "\n";
            break;

        case EventType::MEMBER_LEFT:
            std::cout << "[WS] Member left: "
                      << event.data["username"].get<std::string>() << "\n";
            break;

        case EventType::MEMBER_READY:
            std::cout << "[WS] Member ready status changed: "
                      << event.data["username"].get<std::string>()
                      << " -> " << (event.data["ready"].get<bool>() ? "Ready" : "Not Ready")
                      << "\n";
            break;

        case EventType::QUEUE_ENTERED:
            std::cout << "[WS] Party entered queue: "
                      << event.data["mode"].get<std::string>() << "\n";
            break;

        case EventType::MATCH_FOUND:
            std::cout << "\n🎮 MATCH FOUND! 🎮\n";
            std::cout << "  Match ID: " << event.data["match_id"].get<std::string>() << "\n";
            std::cout << "  Server: " << event.data["server_endpoint"].get<std::string>() << "\n";
            std::cout << "  Mode: " << event.data["mode"].get<std::string>() << "\n";
            found_match_id = event.data["match_id"].get<std::string>();
            match_found = true;
            break;

        case EventType::DISCONNECTED:
            std::cout << "[WS] Disconnected from WebSocket\n";
            break;

        case EventType::ERROR:
            std::cerr << "[WS] Error: " << event.data["error"].get<std::string>() << "\n";
            break;

        default:
            std::cout << "[WS] Unknown event\n";
            break;
    }
}

int main(int argc, char* argv[]) {
    std::string api_url = "http://localhost:8080";
    if (argc > 1) {
        api_url = argv[1];
    }

    std::cout << "=== Matchmaker SDK Full Flow Example ===\n\n";
    std::cout << "Connecting to: " << api_url << "\n\n";

    MatchmakerClient client(api_url);

    // 1. Register and login
    std::cout << "1. Registering new user...\n";
    RegisterRequest reg_req;
    reg_req.username = "sdk_player_" + std::to_string(time(nullptr));
    reg_req.email = reg_req.username + "@example.com";
    reg_req.password = "password123";
    reg_req.region = "us-west";

    auto reg_result = client.auth().register_user(reg_req);
    if (!reg_result) {
        std::cerr << "Registration failed: " << reg_result.error.to_string() << "\n";
        return 1;
    }

    std::cout << "✓ Registered as: " << reg_req.username << "\n\n";
    client.set_auth_token(reg_result.value.access_token);

    // 2. Create a party
    std::cout << "2. Creating party (max size: 5)...\n";
    auto party_result = client.party().create_party(5);
    if (!party_result) {
        std::cerr << "Create party failed: " << party_result.error.to_string() << "\n";
        return 1;
    }

    std::string party_id = party_result.value.party_id;
    std::cout << "✓ Party created: " << party_id << "\n";
    std::cout << "  Leader: " << party_result.value.leader_id << "\n";
    std::cout << "  Size: " << party_result.value.size << "/" << party_result.value.max_size << "\n\n";

    // 3. Register event callbacks
    std::cout << "3. Setting up event handlers...\n";
    client.on_event(EventType::CONNECTED, handle_event);
    client.on_event(EventType::MEMBER_JOINED, handle_event);
    client.on_event(EventType::MEMBER_LEFT, handle_event);
    client.on_event(EventType::MEMBER_READY, handle_event);
    client.on_event(EventType::QUEUE_ENTERED, handle_event);
    client.on_event(EventType::MATCH_FOUND, handle_event);
    client.on_event(EventType::DISCONNECTED, handle_event);
    client.on_event(EventType::ERROR, handle_event);
    std::cout << "✓ Event handlers registered\n\n";

    // Note: WebSocket connection requires modification to MatchmakerClient
    // to expose auth token. For now, this is a placeholder showing the flow.

    // 4. Set ready status
    std::cout << "4. Setting ready status...\n";
    auto ready_result = client.party().set_ready(party_id, true);
    if (!ready_result) {
        std::cerr << "Set ready failed: " << ready_result.error.to_string() << "\n";
        return 1;
    }
    std::cout << "✓ Ready status set\n\n";

    // 5. Enter matchmaking queue
    std::cout << "5. Entering matchmaking queue...\n";
    QueueRequest queue_req;
    queue_req.mode = "ranked";
    queue_req.team_size = 1;  // Solo queue

    auto queue_result = client.party().enter_queue(queue_req);
    if (!queue_result) {
        std::cerr << "Enter queue failed: " << queue_result.error.to_string() << "\n";
        return 1;
    }
    std::cout << "✓ Entered queue (mode: ranked, team_size: 1)\n";
    std::cout << "  Waiting for match...\n\n";

    // 6. Process events while waiting for match
    std::cout << "6. Processing events (waiting for match)...\n";
    auto start_time = std::chrono::steady_clock::now();
    int max_wait_seconds = 60;

    while (!match_found) {
        // Poll for events
        while (auto event = client.poll_event()) {
            // Events are handled by callbacks
        }

        // Check timeout
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - start_time
        ).count();

        if (elapsed >= max_wait_seconds) {
            std::cout << "\n⏱️  Timeout waiting for match\n";
            std::cout << "  (This is expected if no other players are queuing)\n";
            break;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    // 7. If match found, get session details
    if (match_found) {
        std::cout << "\n7. Fetching session details...\n";
        auto session_result = client.session().get_session(found_match_id);
        if (session_result) {
            std::cout << "✓ Session details:\n";
            std::cout << "  Status: " << session_result.value.status << "\n";
            std::cout << "  Server: " << session_result.value.server_endpoint << "\n";
            std::cout << "  Token: " << session_result.value.server_token.substr(0, 20) << "...\n";
            std::cout << "  Players: " << session_result.value.player_ids.size() << "\n\n";

            std::cout << "🎉 Ready to connect to game server!\n";
        }
    } else {
        // Leave queue if no match found
        std::cout << "\n7. Leaving queue...\n";
        auto leave_result = client.party().leave_queue();
        if (leave_result) {
            std::cout << "✓ Left queue\n";
        }
    }

    std::cout << "\n=== Example completed! ===\n";

    return 0;
}
