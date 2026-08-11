// Integration test for the party flow against a live stack.
//
//     make up          # start the platform
//     ./party_test     # exits non-zero if anything is broken
//
// Unlike the unit tests, this exercises the real endpoints and the real party
// WebSocket, so it is what catches SDK/API drift that compiles fine.

#include <game/sdk.hpp>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

using namespace game;

namespace {

int failures = 0;

void check(bool condition, const std::string& what) {
    if (condition) {
        std::cout << "   PASS  " << what << "\n";
    } else {
        std::cout << "   FAIL  " << what << "\n";
        ++failures;
    }
}

// Registers the account, falling back to login when it already exists.
AuthResult authenticate(SDK& sdk, const std::string& username) {
    auto result = sdk.register_user(username + "@test.com", username, "password123", "us-west");
    if (!result.success) {
        result = sdk.login(username, "password123");
    }
    return result;
}

// Leaves any party left behind by an earlier run so the test is repeatable.
void leave_existing_party(SDK& sdk) {
    try {
        const auto profile = sdk.client().get_profile();
        if (!profile.party_id.empty()) {
            sdk.client().leave_party(profile.party_id);
        }
    } catch (const std::exception& e) {
        std::cerr << "   (could not clear a previous party: " << e.what() << ")\n";
    }
}

} // namespace

int main() {
    const std::string base_url = "http://localhost:8080";

    std::cout << "SDK party integration test\n"
              << "==========================\n"
              << "target: " << base_url << "\n\n";

    SDK sdk1(base_url);
    SDK sdk2(base_url);

    std::cout << "1. Authenticating two players\n";
    const auto auth1 = authenticate(sdk1, "Player1");
    const auto auth2 = authenticate(sdk2, "Player2");
    check(auth1.success, "Player1 authenticated");
    check(auth2.success, "Player2 authenticated");
    if (!auth1.success || !auth2.success) {
        std::cerr << "\nCannot continue without both accounts. Is the stack running?\n"
                  << "  player1: " << auth1.error << "\n"
                  << "  player2: " << auth2.error << "\n";
        return 1;
    }

    leave_existing_party(sdk1);
    leave_existing_party(sdk2);

    try {
        std::cout << "\n2. Player1 creates a party\n";
        const auto party = sdk1.client().create_party();
        check(!party.id.empty(), "party has an id");
        check(!party.leader_id.empty(), "party has a leader");
        // Regression: the API returns full member objects under "members".
        // Parsing the wrong field made this silently empty.
        check(party.members.size() == 1, "creator is listed as a member");
        check(party.status == "idle", "new party is idle (got '" + party.status + "')");

        std::cout << "\n3. Player1 subscribes to party events\n";
        std::mutex mtx;
        std::condition_variable cv;
        bool joined_seen = false;
        std::string joined_username;

        sdk1.client().on_lobby_update([&](const LobbyEvent& ev) {
            if (ev.change != LobbyChange::MemberJoined) return;
            {
                std::lock_guard<std::mutex> lock(mtx);
                joined_seen = true;
                joined_username = ev.username;
            }
            cv.notify_one();
        });

        sdk1.client().connect_ws(party.id);
        check(sdk1.client().is_ws_connected(), "party WebSocket connected");

        std::cout << "\n4. Player2 joins the party\n";
        const auto joined = sdk2.client().join_party(party.id);
        check(joined.members.size() == 2, "party now reports two members");

        std::cout << "\n5. member_joined arrives over the WebSocket\n";
        {
            std::unique_lock<std::mutex> lock(mtx);
            const bool got = cv.wait_for(lock, std::chrono::seconds(5), [&] { return joined_seen; });
            check(got, "member_joined delivered within 5s");
            // Regression: lobby events are deltas, so the username has to come
            // through rather than being lost building a half-empty Party.
            check(got && joined_username == "Player2",
                  "event names the joining player (got '" + joined_username + "')");
        }

        std::cout << "\n6. Ready state round-trips\n";
        // The API readies the leader on creation, so only the joiner is not
        // ready at this point. Queueing is refused until everyone is.
        const auto ready = sdk2.client().toggle_ready(party.id);
        check(ready.party_id == party.id, "ready check names the party");
        check(ready.total_count == 2, "ready check counts both members");
        check(ready.ready_count == 2,
              "both players ready (got " + std::to_string(ready.ready_count) + ")");
        check(ready.all_ready, "all_ready is set");
        check(ready.not_ready_players.empty(), "nobody left un-readied");

        std::cout << "\n7. Queue enter and leave\n";
        const auto queued = sdk1.client().enqueue(party.id, "duo", 1);
        check(queued.status == "queueing",
              "party is queueing (got '" + queued.status + "')");

        const auto unqueued = sdk1.client().cancel_queue(party.id);
        check(unqueued.status != "queueing",
              "party left the queue (got '" + unqueued.status + "')");

        std::cout << "\n8. Cleanup\n";
        sdk2.client().leave_party(party.id);
        sdk1.client().leave_party(party.id);
        sdk1.client().disconnect_ws();
        check(!sdk1.client().is_ws_connected(), "WebSocket closed");

    } catch (const std::exception& e) {
        std::cerr << "\nError: " << e.what() << "\n";
        return 1;
    }

    std::cout << "\n";
    if (failures == 0) {
        std::cout << "All checks passed.\n";
        return 0;
    }
    std::cout << failures << " check(s) failed.\n";
    return 1;
}
