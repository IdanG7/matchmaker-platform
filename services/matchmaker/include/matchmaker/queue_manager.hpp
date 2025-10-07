#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <chrono>

namespace matchmaker {

// Player in matchmaking queue
struct QueueEntry {
    std::string party_id;
    std::string region;
    std::string mode;
    int team_size;
    int party_size;
    int avg_mmr;
    std::chrono::system_clock::time_point enqueued_at;
    std::vector<std::string> player_ids;
};

// Match result
struct MatchResult {
    std::string match_id;
    std::string region;
    std::string mode;
    int team_size;
    std::vector<std::vector<std::string>> teams;  // teams[team_idx][player_idx]
    std::vector<std::string> party_ids;
    int avg_mmr;
    int mmr_variance;
    double quality_score;
};

// Queue bucket key (region + mode)
struct QueueBucket {
    std::string region;
    std::string mode;
    int team_size;

    std::string key() const {
        return region + ":" + mode + ":" + std::to_string(team_size);
    }

    bool operator==(const QueueBucket& other) const {
        return region == other.region && mode == other.mode && team_size == other.team_size;
    }
};

struct QueueBucketHash {
    std::size_t operator()(const QueueBucket& bucket) const {
        return std::hash<std::string>{}(bucket.key());
    }
};

// Configuration for queue management
struct QueueConfig {
    int mmr_band_initial = 100;           // Initial MMR range (±100)
    int mmr_band_max = 500;               // Max MMR range (±500)
    int mmr_band_growth_per_sec = 10;     // MMR range growth rate
    int max_wait_time_sec = 120;          // Max queue time before timeout
    double min_match_quality = 0.6;       // Minimum acceptable match quality (0-1)
};

/**
 * QueueManager - Manages matchmaking queues and team formation
 */
class QueueManager {
public:
    explicit QueueManager(const QueueConfig& config = QueueConfig{});
    ~QueueManager() = default;

    // Queue operations
    void enqueue(const QueueEntry& entry);
    void dequeue(const std::string& party_id);
    bool is_queued(const std::string& party_id) const;

    // Matchmaking tick
    std::vector<MatchResult> tick();

    // Stats
    size_t get_queue_size() const;
    size_t get_queue_size(const QueueBucket& bucket) const;
    std::unordered_map<std::string, size_t> get_bucket_sizes() const;

private:
    QueueConfig config_;

    // Queue storage: bucket -> list of queue entries
    std::unordered_map<QueueBucket, std::vector<QueueEntry>, QueueBucketHash> buckets_;

    // Fast lookup: party_id -> bucket
    std::unordered_map<std::string, QueueBucket> party_to_bucket_;

    // Helper methods
    int calculate_mmr_band(const QueueEntry& entry, std::chrono::system_clock::time_point now) const;
    std::vector<MatchResult> process_bucket(QueueBucket bucket, std::vector<QueueEntry>& entries);
    void remove_matched_parties(std::vector<QueueEntry>& entries, const std::vector<std::string>& party_ids);
    void remove_timed_out_entries(std::vector<QueueEntry>& entries, std::chrono::system_clock::time_point now);
};

} // namespace matchmaker
