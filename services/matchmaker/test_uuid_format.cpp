#include "include/matchmaker/queue_manager.hpp"
#include <iostream>
#include <regex>

int main() {
    matchmaker::QueueConfig config;
    config.mmr_band_initial = 100;
    config.mmr_band_max = 500;
    config.mmr_band_growth_per_sec = 10;
    config.max_wait_time_sec = 120;
    config.min_match_quality = 0.5;

    matchmaker::QueueManager qm(config);

    // Create entries and form match to get match_id
    std::vector<matchmaker::QueueEntry> entries;
    for (int i = 0; i < 10; ++i) {
        matchmaker::QueueEntry entry;
        entry.party_id = "party" + std::to_string(i);
        entry.region = "us-west";
        entry.mode = "ranked";
        entry.team_size = 5;
        entry.party_size = 1;
        entry.avg_mmr = 1500;
        entry.enqueued_at = std::chrono::system_clock::now();
        entry.player_ids.push_back("player" + std::to_string(i));
        qm.enqueue(entry);
    }

    auto matches = qm.tick();
    
    if (matches.size() > 0) {
        std::string match_id = matches[0].match_id;
        std::cout << "Generated match_id: " << match_id << std::endl;
        
        // UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        std::regex uuid_regex("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
        
        if (std::regex_match(match_id, uuid_regex)) {
            std::cout << "✓ Valid UUID v4 format!" << std::endl;
            return 0;
        } else {
            std::cout << "✗ Invalid UUID format!" << std::endl;
            return 1;
        }
    } else {
        std::cout << "No match created" << std::endl;
        return 1;
    }
}
