#include "matchmaker/queue_manager.hpp"
#include "matchmaker/nats_client.hpp"
#include <spdlog/spdlog.h>
#include <iostream>
#include <chrono>
#include <thread>
#include <csignal>
#include <atomic>

namespace {
std::atomic<bool> g_running{true};

void signal_handler(int signal) {
    if (signal == SIGINT || signal == SIGTERM) {
        spdlog::info("Received shutdown signal");
        g_running = false;
    }
}
}

int main() {
    // Setup logging
    spdlog::set_level(spdlog::level::info);
    spdlog::info("Matchmaker service starting...");

    // Setup signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    // Configuration
    matchmaker::QueueConfig config;
    config.mmr_band_initial = 100;
    config.mmr_band_max = 500;
    config.mmr_band_growth_per_sec = 10;
    config.max_wait_time_sec = 120;
    config.min_match_quality = 0.6;

    // Initialize queue manager
    matchmaker::QueueManager queue_manager(config);

    // Initialize NATS client (mock for now)
    auto nats = matchmaker::create_nats_client(true);

    if (!nats->connect("nats://localhost:4222")) {
        spdlog::error("Failed to connect to NATS");
        return 1;
    }

    // Subscribe to queue events
    nats->subscribe_queue_events(
        "matchmaker.queue.*",
        [&queue_manager](const matchmaker::QueueEntry& entry) {
            spdlog::info("Queue event: party={}, region={}, mode={}, mmr={}",
                entry.party_id, entry.region, entry.mode, entry.avg_mmr);
            queue_manager.enqueue(entry);
        }
    );

    spdlog::info("Matchmaker service running. Press Ctrl+C to stop.");

    // Main tick loop
    const int tick_interval_ms = 200;
    auto last_stats_time = std::chrono::steady_clock::now();
    size_t total_matches = 0;

    while (g_running) {
        auto tick_start = std::chrono::steady_clock::now();

        // Process matchmaking
        auto matches = queue_manager.tick();

        // Publish match found events
        for (const auto& match : matches) {
            spdlog::info("Match formed: id={}, region={}, mode={}, mmr={}, quality={:.2f}",
                match.match_id, match.region, match.mode, match.avg_mmr, match.quality_score);

            nats->publish_match_found(match);
            total_matches++;
        }

        // Log stats every 10 seconds
        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_stats_time).count() >= 10) {
            auto bucket_sizes = queue_manager.get_bucket_sizes();
            spdlog::info("Stats: total_queued={}, total_matches={}, buckets={}",
                queue_manager.get_queue_size(), total_matches, bucket_sizes.size());

            for (const auto& [bucket, size] : bucket_sizes) {
                spdlog::debug("  Bucket {}: {} parties", bucket, size);
            }

            last_stats_time = now;
        }

        // Sleep for remainder of tick interval
        auto tick_duration = std::chrono::steady_clock::now() - tick_start;
        auto sleep_time = std::chrono::milliseconds(tick_interval_ms) - tick_duration;

        if (sleep_time.count() > 0) {
            std::this_thread::sleep_for(sleep_time);
        } else {
            spdlog::warn("Tick took longer than {}ms: {}ms",
                tick_interval_ms,
                std::chrono::duration_cast<std::chrono::milliseconds>(tick_duration).count());
        }
    }

    spdlog::info("Matchmaker service shutting down...");
    nats->disconnect();

    return 0;
}
