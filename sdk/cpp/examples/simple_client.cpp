// End-to-end SDK example: authenticate, form a party, queue for a match, and
// wait for the matchmaker to hand back a game server to connect to.
//
// Run two of these side by side against a live stack to actually get matched:
//
//     example_client --username alice --password password123
//     example_client --username bob   --password password123
//
// Each one registers on first run and logs in afterwards. A match needs enough
// players to fill both teams, so a solo run will sit in the queue until a
// second client shows up.

#include <game/sdk.hpp>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>

namespace {

struct Options {
    std::string url = "http://localhost:8080";
    std::string username = "player1";
    std::string password = "password123";
    std::string email;  // defaults to <username>@example.com
    std::string region = "us-west";
    std::string mode = "duo";
    int team_size = 1;
    int timeout_seconds = 120;
};

void print_usage(const char* argv0) {
    std::cout
        << "Usage: " << argv0 << " [options]\n"
        << "  --url URL            matchmaker base URL (default http://localhost:8080)\n"
        << "  --username NAME      account username (default player1)\n"
        << "  --password PASS      account password (default password123)\n"
        << "  --email ADDR         used only on first registration\n"
        << "  --region REGION      matchmaking region (default us-west)\n"
        << "  --mode MODE          queue mode (default duo)\n"
        << "  --team-size N        players per team (default 1)\n"
        << "  --timeout SECONDS    how long to wait in queue (default 120)\n"
        << "  --help               show this message\n";
}

// Returns false if the caller should exit (bad args or --help).
bool parse_args(int argc, char** argv, Options& opts) {
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        auto next = [&](const char* name) -> std::string {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << name << "\n";
                return {};
            }
            return argv[++i];
        };

        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return false;
        } else if (arg == "--url") {
            opts.url = next("--url");
        } else if (arg == "--username") {
            opts.username = next("--username");
        } else if (arg == "--password") {
            opts.password = next("--password");
        } else if (arg == "--email") {
            opts.email = next("--email");
        } else if (arg == "--region") {
            opts.region = next("--region");
        } else if (arg == "--mode") {
            opts.mode = next("--mode");
        } else if (arg == "--team-size") {
            opts.team_size = std::atoi(next("--team-size").c_str());
        } else if (arg == "--timeout") {
            opts.timeout_seconds = std::atoi(next("--timeout").c_str());
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            print_usage(argv[0]);
            return false;
        }
    }
    if (opts.email.empty()) {
        opts.email = opts.username + "@example.com";
    }
    return true;
}

const char* change_name(game::LobbyChange change) {
    switch (change) {
    case game::LobbyChange::MemberJoined:  return "member joined";
    case game::LobbyChange::MemberLeft:    return "member left";
    case game::LobbyChange::MemberReady:   return "ready changed";
    case game::LobbyChange::QueueEntered:  return "queue entered";
    case game::LobbyChange::QueueLeft:     return "queue left";
    case game::LobbyChange::PartyUpdated:  return "party updated";
    }
    return "unknown";
}

} // namespace

int main(int argc, char** argv) {
    Options opts;
    if (!parse_args(argc, argv, opts)) {
        return argc > 1 && std::string(argv[1]) == "--help" ? 0 : 1;
    }

    std::cout << "Matchmaker SDK example\n"
              << "======================\n"
              << "server: " << opts.url << "\n"
              << "player: " << opts.username << "\n\n";

    game::SDK sdk(opts.url);

    // 1. Authenticate. Register first; if the account already exists, log in.
    std::cout << "[1/6] authenticating\n";
    auto auth = sdk.register_user(opts.email, opts.username, opts.password, opts.region);
    if (!auth.success) {
        std::cout << "      registration declined (" << auth.error << "), logging in\n";
        auth = sdk.login(opts.username, opts.password);
    }
    if (!auth.success) {
        std::cerr << "      failed: " << auth.error << "\n";
        return 1;
    }
    std::cout << "      authenticated\n";

    try {
        // 2. Confirm who we are.
        const auto profile = sdk.client().get_profile();
        std::cout << "[2/6] profile: " << profile.username << "  mmr=" << profile.mmr
                  << "  region=" << profile.region << "\n";

        // 3. Create a party. Matchmaking always operates on parties, even solo.
        //
        // An earlier run that exited before leaving leaves the account in a
        // party, and create_party is refused while that is true. The profile
        // reports it, so the stale one can be abandoned first rather than the
        // account being stuck for good.
        if (!profile.party_id.empty()) {
            std::cout << "      leaving party " << profile.party_id
                      << " left over from an earlier run\n";
            sdk.client().leave_party(profile.party_id);
        }

        const auto party = sdk.client().create_party();
        std::cout << "[3/6] party " << party.id << " created (" << party.size << "/"
                  << party.max_size << ")\n";

        // 4. Subscribe before queueing so no event is missed.
        std::mutex mtx;
        std::condition_variable cv;
        bool matched = false;
        game::MatchInfo match;

        sdk.client().on_lobby_update([](const game::LobbyEvent& ev) {
            std::cout << "      [lobby] " << change_name(ev.change);
            if (!ev.username.empty()) std::cout << ": " << ev.username;
            if (ev.change == game::LobbyChange::MemberReady) {
                std::cout << (ev.ready ? " is ready" : " is not ready");
            }
            std::cout << "\n";
        });

        sdk.client().on_match_found([&](const game::MatchInfo& info) {
            {
                std::lock_guard<std::mutex> lock(mtx);
                match = info;
                matched = true;
            }
            cv.notify_one();
        });

        sdk.client().connect_ws(party.id);
        std::cout << "[4/6] listening for party events\n";

        // 5. Ready up, then enter the queue. set_ready is used rather than
        // toggle_ready because the API readies whoever created the party, and
        // toggling would take us straight back out of the queue's reach.
        const auto ready = sdk.client().set_ready(party.id, true);
        std::cout << "[5/6] ready " << ready.ready_count << "/" << ready.total_count << "\n";

        const auto queued = sdk.client().enqueue(party.id, opts.mode, opts.team_size);
        std::cout << "      queued for " << opts.mode << " (team size " << opts.team_size
                  << "), party status=" << queued.status << "\n";

        // 6. Wait for the matchmaker.
        std::cout << "[6/6] waiting up to " << opts.timeout_seconds
                  << "s for a match (run a second client to fill the lobby)\n";

        std::unique_lock<std::mutex> lock(mtx);
        const bool got_match = cv.wait_for(lock, std::chrono::seconds(opts.timeout_seconds),
                                           [&] { return matched; });

        if (!got_match) {
            lock.unlock();
            std::cout << "\nNo match within the timeout. Leaving the queue.\n";
            sdk.client().cancel_queue(party.id);
            sdk.client().leave_party(party.id);
            sdk.client().disconnect_ws();
            return 1;
        }

        const game::MatchInfo found = match;
        lock.unlock();

        std::cout << "\nMatch found\n"
                  << "  match_id: " << found.match_id << "\n"
                  << "  endpoint: " << found.server_endpoint << "\n"
                  << "  mode:     " << found.mode << " (" << found.region << ")\n";

        for (size_t i = 0; i < found.teams.size(); ++i) {
            std::cout << "  team " << i << ":  ";
            for (const auto& player : found.teams[i]) std::cout << player << " ";
            std::cout << "\n";
        }

        // This is what a real game client hands to its network layer: the
        // address to dial, and the token proving it belongs in this match.
        std::string host;
        uint16_t port = 0;
        if (found.split_endpoint(host, port)) {
            std::cout << "\nConnect your game client to " << host << ":" << port
                      << "\n  session token: " << found.server_token.substr(0, 16) << "...\n";
        } else {
            std::cerr << "\nMatchmaker returned an unusable endpoint: '"
                      << found.server_endpoint << "'\n";
            sdk.client().disconnect_ws();
            return 1;
        }

        sdk.client().disconnect_ws();
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "\nError: " << e.what() << "\n";
        return 1;
    }
}
