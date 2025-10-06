#pragma once

#include <string>
#include <vector>
#include <memory>

namespace matchmaker {

// Configuration for matchmaker
struct Config {
    std::string redis_url;
    std::string nats_url;
    int tick_interval_ms = 200;
    int max_wait_time_seconds = 120;
    int mmr_band_initial = 100;
    int mmr_band_max = 500;
    int mmr_band_growth_per_second = 10;
};

// Player in queue
struct QueuedPlayer {
    std::string player_id;
    std::string party_id;
    int mmr;
    std::string region;
    int64_t enqueued_at;
};

// Match result
struct Match {
    std::string match_id;
    std::string region;
    std::string mode;
    std::vector<std::vector<std::string>> teams;
    int mmr_avg;
};

// Main matchmaker class (to be implemented in Phase 4)
class Matchmaker {
public:
    explicit Matchmaker(const Config& config);
    ~Matchmaker();

    // Tick the matchmaker (process queues)
    void tick();

    // Queue operations
    void enqueue(const QueuedPlayer& player);
    void dequeue(const std::string& player_id);

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace matchmaker
