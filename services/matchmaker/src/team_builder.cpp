#include "matchmaker/team_builder.hpp"
#include <algorithm>
#include <numeric>
#include <cmath>

namespace matchmaker {

std::optional<MatchResult> TeamBuilder::try_form_match(
    const std::vector<QueueEntry>& entries,
    int team_size,
    int num_teams,
    int mmr_tolerance
) {
    if (entries.empty()) {
        return std::nullopt;
    }

    int total_players_needed = team_size * num_teams;

    // Convert to pointers for easier manipulation
    std::vector<const QueueEntry*> candidates;
    int total_available = 0;

    for (const auto& entry : entries) {
        candidates.push_back(&entry);
        total_available += entry.party_size;
    }

    // Check if we have enough players
    if (total_available < total_players_needed) {
        return std::nullopt;
    }

    // Try to find a valid combination
    // Start with the smallest set that has enough players
    for (size_t combo_size = 2; combo_size <= candidates.size(); ++combo_size) {
        // Generate combinations of the right size
        std::vector<const QueueEntry*> combination;
        combination.reserve(combo_size);

        // Use greedy approach: take first combo_size entries
        int player_count = 0;
        for (size_t i = 0; i < combo_size && i < candidates.size(); ++i) {
            combination.push_back(candidates[i]);
            player_count += candidates[i]->party_size;
        }

        // Check if this combination works
        if (player_count < total_players_needed) {
            continue;
        }

        if (!is_valid_combination(combination, team_size, num_teams, mmr_tolerance)) {
            continue;
        }

        // Form teams using greedy balancing
        auto teams = balance_teams(combination, num_teams);

        if (teams.empty()) {
            continue;
        }

        // Build match result
        MatchResult result;
        result.teams.resize(num_teams);
        result.avg_mmr = 0;
        int total_players = 0;

        for (size_t team_idx = 0; team_idx < teams.size(); ++team_idx) {
            for (const auto* entry : teams[team_idx]) {
                // Add all players from this party to the team
                for (const auto& player_id : entry->player_ids) {
                    result.teams[team_idx].push_back(player_id);
                }
                result.party_ids.push_back(entry->party_id);
                result.avg_mmr += entry->avg_mmr * entry->party_size;
                total_players += entry->party_size;
            }
        }

        result.avg_mmr /= total_players;
        result.mmr_variance = calculate_mmr_variance(combination);
        result.quality_score = calculate_match_quality(result, entries);

        return result;
    }

    return std::nullopt;
}

double TeamBuilder::calculate_match_quality(
    const MatchResult& match,
    const std::vector<QueueEntry>& entries
) {
    // Factor 1: MMR balance between teams (0-1, higher is better)
    std::vector<int> team_mmrs;
    for (const auto& team : match.teams) {
        int team_mmr = 0;
        int team_size = 0;
        for (const auto& player_id : team) {
            // Find this player's MMR from entries
            for (const auto& entry : entries) {
                if (std::find(entry.player_ids.begin(), entry.player_ids.end(), player_id)
                    != entry.player_ids.end()) {
                    team_mmr += entry.avg_mmr;
                    team_size++;
                    break;
                }
            }
        }
        if (team_size > 0) {
            team_mmrs.push_back(team_mmr / team_size);
        }
    }

    // Calculate MMR difference between teams
    double mmr_balance = 1.0;
    if (team_mmrs.size() >= 2) {
        int max_mmr = *std::max_element(team_mmrs.begin(), team_mmrs.end());
        int min_mmr = *std::min_element(team_mmrs.begin(), team_mmrs.end());
        int mmr_diff = max_mmr - min_mmr;
        mmr_balance = 1.0 - (std::min(mmr_diff, 500) / 500.0);  // Normalize to 0-1
    }

    // Factor 2: Low MMR variance within match (0-1, lower variance is better)
    double variance_score = 1.0 - (std::min(match.mmr_variance, 1000) / 1000.0);

    // Factor 3: Wait time fairness (currently simple, could be improved)
    double wait_score = 1.0;  // Simplified for now

    // Weighted average
    return (mmr_balance * 0.5) + (variance_score * 0.3) + (wait_score * 0.2);
}

int TeamBuilder::calculate_avg_mmr(const std::vector<const QueueEntry*>& entries) {
    if (entries.empty()) {
        return 0;
    }

    int total_mmr = 0;
    int total_players = 0;

    for (const auto* entry : entries) {
        total_mmr += entry->avg_mmr * entry->party_size;
        total_players += entry->party_size;
    }

    return total_players > 0 ? total_mmr / total_players : 0;
}

int TeamBuilder::calculate_mmr_variance(const std::vector<const QueueEntry*>& entries) {
    if (entries.empty()) {
        return 0;
    }

    int avg_mmr = calculate_avg_mmr(entries);
    int sum_squared_diff = 0;
    int total_players = 0;

    for (const auto* entry : entries) {
        int diff = entry->avg_mmr - avg_mmr;
        sum_squared_diff += (diff * diff) * entry->party_size;
        total_players += entry->party_size;
    }

    return total_players > 0 ? std::sqrt(sum_squared_diff / total_players) : 0;
}

std::vector<std::vector<const QueueEntry*>> TeamBuilder::balance_teams(
    std::vector<const QueueEntry*> entries,
    int num_teams
) {
    // Sort by MMR descending for snake draft
    std::sort(entries.begin(), entries.end(),
        [](const QueueEntry* a, const QueueEntry* b) {
            return a->avg_mmr > b->avg_mmr;
        });

    std::vector<std::vector<const QueueEntry*>> teams(num_teams);
    std::vector<int> team_mmr_sums(num_teams, 0);
    std::vector<int> team_player_counts(num_teams, 0);

    // Greedy assignment: assign each party to the team with lowest total MMR
    for (const auto* entry : entries) {
        // Find team with lowest MMR sum
        int min_team_idx = 0;
        int min_mmr = team_mmr_sums[0];

        for (int i = 1; i < num_teams; ++i) {
            if (team_mmr_sums[i] < min_mmr) {
                min_mmr = team_mmr_sums[i];
                min_team_idx = i;
            }
        }

        // Assign to this team
        teams[min_team_idx].push_back(entry);
        team_mmr_sums[min_team_idx] += entry->avg_mmr * entry->party_size;
        team_player_counts[min_team_idx] += entry->party_size;
    }

    return teams;
}

bool TeamBuilder::is_valid_combination(
    const std::vector<const QueueEntry*>& entries,
    int team_size,
    int num_teams,
    int mmr_tolerance
) {
    // Count total players
    int total_players = 0;
    for (const auto* entry : entries) {
        total_players += entry->party_size;
    }

    int required_players = team_size * num_teams;
    if (total_players < required_players) {
        return false;
    }

    // Check MMR range
    int min_mmr = entries[0]->avg_mmr;
    int max_mmr = entries[0]->avg_mmr;

    for (const auto* entry : entries) {
        min_mmr = std::min(min_mmr, entry->avg_mmr);
        max_mmr = std::max(max_mmr, entry->avg_mmr);
    }

    return (max_mmr - min_mmr) <= mmr_tolerance;
}

} // namespace matchmaker
