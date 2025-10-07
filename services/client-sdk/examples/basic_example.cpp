/**
 * Basic example demonstrating SDK usage.
 * Shows registration, login, and profile retrieval.
 */

#include "matchmaker/matchmaker_client.hpp"
#include <iostream>
#include <string>

using namespace matchmaker;

int main(int argc, char* argv[]) {
    // Configuration
    std::string api_url = "http://localhost:8080";
    if (argc > 1) {
        api_url = argv[1];
    }

    std::cout << "=== Matchmaker SDK Basic Example ===\n\n";
    std::cout << "Connecting to: " << api_url << "\n\n";

    // Create client
    MatchmakerClient client(api_url);

    // Register a new user
    std::cout << "1. Registering new user...\n";
    RegisterRequest reg_req;
    reg_req.username = "sdk_user_" + std::to_string(time(nullptr));
    reg_req.email = reg_req.username + "@example.com";
    reg_req.password = "secure_password_123";
    reg_req.region = "us-west";

    auto reg_result = client.auth().register_user(reg_req);

    if (!reg_result) {
        std::cerr << "Registration failed: " << reg_result.error.to_string() << "\n";
        return 1;
    }

    std::cout << "✓ Registered successfully\n";
    std::cout << "  Access Token: " << reg_result.value.access_token.substr(0, 20) << "...\n\n";

    // Set auth token for subsequent requests
    client.set_auth_token(reg_result.value.access_token);

    // Get profile
    std::cout << "2. Fetching profile...\n";
    auto profile_result = client.profile().get_profile();

    if (!profile_result) {
        std::cerr << "Get profile failed: " << profile_result.error.to_string() << "\n";
        return 1;
    }

    std::cout << "✓ Profile retrieved\n";
    std::cout << "  Player ID: " << profile_result.value.player_id << "\n";
    std::cout << "  Username:  " << profile_result.value.username << "\n";
    std::cout << "  Email:     " << profile_result.value.email << "\n";
    std::cout << "  Region:    " << profile_result.value.region << "\n";
    std::cout << "  MMR:       " << profile_result.value.mmr << "\n\n";

    // Update profile (change region)
    std::cout << "3. Updating profile (changing region to us-east)...\n";
    ProfileUpdateRequest update_req;
    update_req.region = "us-east";

    auto update_result = client.profile().update_profile(update_req);

    if (!update_result) {
        std::cerr << "Update profile failed: " << update_result.error.to_string() << "\n";
        return 1;
    }

    std::cout << "✓ Profile updated\n";
    std::cout << "  New Region: " << update_result.value.region << "\n\n";

    std::cout << "=== Example completed successfully! ===\n";

    return 0;
}
