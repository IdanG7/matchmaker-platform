#pragma once

#include "queue_manager.hpp"
#include <vector>
#include <optional>

namespace matchmaker {

/**
 * TeamBuilder - Algorithms for forming balanced teams from queue entries
 */
class TeamBuilder {
public:
    /**
     * Attempt to form a match from a list of queue entries.
     *
     * @param entries List of parties in queue (sorted by wait time)
     * @param team_size Number of players per team
     * @param num_teams Number of teams (usually 2)
     * @param mmr_tolerance Maximum allowed MMR difference
     * @return MatchResult if successful, nullopt otherwise
     */
    static std::optional<MatchResult> try_form_match(
        const std::vector<QueueEntry>& entries,
        int team_size,
        int num_teams,
        int mmr_tolerance
    );

    /**
     * Calculate match quality score (0-1, higher is better)
     *
     * Factors:
     * - MMR balance between teams
     * - MMR variance within teams
     * - Wait time fairness
     *
     * @param match The match to score
     * @param entries Original queue entries
     * @return Quality score (0.0 = poor, 1.0 = perfect)
     */
    static double calculate_match_quality(
        const MatchResult& match,
        const std::vector<QueueEntry>& entries
    );

private:
    // Helper: Calculate average MMR for a list of entries
    static int calculate_avg_mmr(const std::vector<const QueueEntry*>& entries);

    // Helper: Calculate MMR variance
    static int calculate_mmr_variance(const std::vector<const QueueEntry*>& entries);

    // Helper: Greedy team balancing algorithm
    static std::vector<std::vector<const QueueEntry*>> balance_teams(
        std::vector<const QueueEntry*> entries,
        int num_teams
    );

    // Helper: Check if combination is valid (enough players, MMR within tolerance)
    static bool is_valid_combination(
        const std::vector<const QueueEntry*>& entries,
        int team_size,
        int num_teams,
        int mmr_tolerance
    );
};

} // namespace matchmaker
