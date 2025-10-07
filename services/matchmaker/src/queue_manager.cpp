#include "matchmaker/queue_manager.hpp"
#include "matchmaker/team_builder.hpp"
#include <algorithm>
#include <random>
#include <sstream>
#include <iomanip>

namespace matchmaker {

QueueManager::QueueManager(const QueueConfig& config)
    : config_(config) {}

void QueueManager::enqueue(const QueueEntry& entry) {
    QueueBucket bucket{entry.region, entry.mode, entry.team_size};

    // Add to bucket
    buckets_[bucket].push_back(entry);

    // Track party for fast lookup
    party_to_bucket_[entry.party_id] = bucket;
}

void QueueManager::dequeue(const std::string& party_id) {
    // Find which bucket this party is in
    auto it = party_to_bucket_.find(party_id);
    if (it == party_to_bucket_.end()) {
        return;  // Party not in queue
    }

    QueueBucket bucket = it->second;
    auto& entries = buckets_[bucket];

    // Remove from bucket
    entries.erase(
        std::remove_if(entries.begin(), entries.end(),
            [&party_id](const QueueEntry& e) { return e.party_id == party_id; }),
        entries.end()
    );

    // Remove from lookup
    party_to_bucket_.erase(it);
}

bool QueueManager::is_queued(const std::string& party_id) const {
    return party_to_bucket_.find(party_id) != party_to_bucket_.end();
}

std::vector<MatchResult> QueueManager::tick() {
    std::vector<MatchResult> matches;
    auto now = std::chrono::system_clock::now();

    // Process each bucket independently
    for (auto& [bucket, entries] : buckets_) {
        // Always remove timed-out entries, even from small buckets
        remove_timed_out_entries(entries, now);

        if (entries.size() < 2) {
            continue;  // Need at least 2 parties to form a match
        }

        // Try to form matches
        auto bucket_matches = process_bucket(bucket, entries);
        matches.insert(matches.end(), bucket_matches.begin(), bucket_matches.end());
    }

    return matches;
}

std::vector<MatchResult> QueueManager::process_bucket(
    QueueBucket bucket,
    std::vector<QueueEntry>& entries
) {
    std::vector<MatchResult> matches;
    auto now = std::chrono::system_clock::now();

    // Sort by wait time (longest waiting first - fairness)
    std::sort(entries.begin(), entries.end(),
        [](const QueueEntry& a, const QueueEntry& b) {
            return a.enqueued_at < b.enqueued_at;
        });

    // Try to form matches until we can't anymore
    while (entries.size() >= 2) {
        // Calculate MMR band for the longest-waiting party
        int mmr_tolerance = calculate_mmr_band(entries[0], now);

        // Attempt to form a match
        auto match_opt = TeamBuilder::try_form_match(
            entries,
            bucket.team_size,
            2,  // 2 teams (can be configurable later)
            mmr_tolerance
        );

        if (!match_opt.has_value()) {
            // Can't form any more matches in this bucket
            break;
        }

        MatchResult match = match_opt.value();

        // Check quality threshold
        if (match.quality_score < config_.min_match_quality) {
            // Match quality too low, wait for better options
            break;
        }

        // Generate UUID v4 for match ID
        static std::random_device rd;
        static std::mt19937 gen(rd());
        static std::uniform_int_distribution<uint32_t> dis;

        // UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        std::stringstream ss;
        ss << std::hex << std::setfill('0');
        ss << std::setw(8) << dis(gen) << "-";
        ss << std::setw(4) << (dis(gen) & 0xFFFF) << "-";
        ss << std::setw(4) << ((dis(gen) & 0x0FFF) | 0x4000) << "-";  // Version 4
        ss << std::setw(4) << ((dis(gen) & 0x3FFF) | 0x8000) << "-";  // Variant
        ss << std::setw(8) << dis(gen);
        ss << std::setw(4) << (dis(gen) & 0xFFFF);
        match.match_id = ss.str();

        // Fill in region/mode from bucket
        match.region = bucket.region;
        match.mode = bucket.mode;
        match.team_size = bucket.team_size;

        matches.push_back(match);

        // Remove matched parties from queue
        remove_matched_parties(entries, match.party_ids);

        // Also remove from lookup map
        for (const auto& party_id : match.party_ids) {
            party_to_bucket_.erase(party_id);
        }
    }

    return matches;
}

int QueueManager::calculate_mmr_band(
    const QueueEntry& entry,
    std::chrono::system_clock::time_point now
) const {
    auto wait_time_sec = std::chrono::duration_cast<std::chrono::seconds>(
        now - entry.enqueued_at
    ).count();

    int band = config_.mmr_band_initial + (wait_time_sec * config_.mmr_band_growth_per_sec);
    return std::min(band, config_.mmr_band_max);
}

void QueueManager::remove_matched_parties(
    std::vector<QueueEntry>& entries,
    const std::vector<std::string>& party_ids
) {
    entries.erase(
        std::remove_if(entries.begin(), entries.end(),
            [&party_ids](const QueueEntry& e) {
                return std::find(party_ids.begin(), party_ids.end(), e.party_id) != party_ids.end();
            }),
        entries.end()
    );
}

void QueueManager::remove_timed_out_entries(
    std::vector<QueueEntry>& entries,
    std::chrono::system_clock::time_point now
) {
    auto timeout_duration = std::chrono::seconds(config_.max_wait_time_sec);

    entries.erase(
        std::remove_if(entries.begin(), entries.end(),
            [&](const QueueEntry& e) {
                auto wait_time = now - e.enqueued_at;
                return wait_time > timeout_duration;
            }),
        entries.end()
    );
}

size_t QueueManager::get_queue_size() const {
    size_t total = 0;
    for (const auto& [bucket, entries] : buckets_) {
        total += entries.size();
    }
    return total;
}

size_t QueueManager::get_queue_size(const QueueBucket& bucket) const {
    auto it = buckets_.find(bucket);
    if (it == buckets_.end()) {
        return 0;
    }
    return it->second.size();
}

std::unordered_map<std::string, size_t> QueueManager::get_bucket_sizes() const {
    std::unordered_map<std::string, size_t> sizes;
    for (const auto& [bucket, entries] : buckets_) {
        sizes[bucket.key()] = entries.size();
    }
    return sizes;
}

} // namespace matchmaker
