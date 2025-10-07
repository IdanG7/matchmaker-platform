#include "matchmaker/queue_manager.hpp"
#include "matchmaker/team_builder.hpp"
#include <gtest/gtest.h>
#include <chrono>
#include <thread>

using namespace matchmaker;

class QueueManagerTest : public ::testing::Test {
protected:
    QueueConfig config;
    std::unique_ptr<QueueManager> queue_manager;

    void SetUp() override {
        config.mmr_band_initial = 100;
        config.mmr_band_max = 500;
        config.mmr_band_growth_per_sec = 10;
        config.max_wait_time_sec = 5;  // Short timeout for testing
        config.min_match_quality = 0.5;

        queue_manager = std::make_unique<QueueManager>(config);
    }

    QueueEntry create_entry(const std::string& party_id, int mmr, int party_size = 1) {
        QueueEntry entry;
        entry.party_id = party_id;
        entry.region = "us-west";
        entry.mode = "ranked";
        entry.team_size = 5;
        entry.party_size = party_size;
        entry.avg_mmr = mmr;
        entry.enqueued_at = std::chrono::system_clock::now();

        for (int i = 0; i < party_size; ++i) {
            entry.player_ids.push_back(party_id + "_player" + std::to_string(i));
        }

        return entry;
    }
};

TEST_F(QueueManagerTest, EnqueueDequeue) {
    auto entry = create_entry("party1", 1500);

    queue_manager->enqueue(entry);
    EXPECT_EQ(queue_manager->get_queue_size(), 1);
    EXPECT_TRUE(queue_manager->is_queued("party1"));

    queue_manager->dequeue("party1");
    EXPECT_EQ(queue_manager->get_queue_size(), 0);
    EXPECT_FALSE(queue_manager->is_queued("party1"));
}

TEST_F(QueueManagerTest, SimpleMatchFormation) {
    // Create 10 solo players with similar MMR for a 5v5 match
    for (int i = 0; i < 10; ++i) {
        auto entry = create_entry("party" + std::to_string(i), 1500 + i * 10, 1);
        queue_manager->enqueue(entry);
    }

    EXPECT_EQ(queue_manager->get_queue_size(), 10);

    // Tick should form a match
    auto matches = queue_manager->tick();

    ASSERT_EQ(matches.size(), 1);
    EXPECT_EQ(matches[0].teams.size(), 2);
    EXPECT_EQ(matches[0].teams[0].size() + matches[0].teams[1].size(), 10);

    // Queue should be empty after match
    EXPECT_EQ(queue_manager->get_queue_size(), 0);
}

TEST_F(QueueManagerTest, MMRBandWidening) {
    // Two players with different MMR
    auto entry1 = create_entry("party1", 1000, 1);
    auto entry2 = create_entry("party2", 1300, 1);  // 300 MMR difference

    // Initially won't match (tolerance = 100)
    queue_manager->enqueue(entry1);
    queue_manager->enqueue(entry2);

    auto matches = queue_manager->tick();
    EXPECT_EQ(matches.size(), 0);

    // Wait for MMR band to widen
    // After 20 seconds: band = 100 + 20*10 = 300 (still not enough for 5v5)
    // Need more players anyway for 5v5
}

TEST_F(QueueManagerTest, PartySizeRespected) {
    // Create a party of 3 and 7 solo players (total 10 for 5v5)
    auto party_entry = create_entry("party_of_3", 1500, 3);
    queue_manager->enqueue(party_entry);

    for (int i = 0; i < 7; ++i) {
        auto solo = create_entry("solo" + std::to_string(i), 1500, 1);
        queue_manager->enqueue(solo);
    }

    EXPECT_EQ(queue_manager->get_queue_size(), 8);  // 8 parties

    auto matches = queue_manager->tick();

    ASSERT_EQ(matches.size(), 1);
    // Total 10 players across all teams
    int total_players = 0;
    for (const auto& team : matches[0].teams) {
        total_players += team.size();
    }
    EXPECT_EQ(total_players, 10);
}

TEST_F(QueueManagerTest, DifferentRegionsDontMatch) {
    auto us_entry = create_entry("us_party", 1500);
    us_entry.region = "us-west";

    auto eu_entry = create_entry("eu_party", 1500);
    eu_entry.region = "eu-west";

    queue_manager->enqueue(us_entry);
    queue_manager->enqueue(eu_entry);

    auto matches = queue_manager->tick();

    // Should not form a match across regions
    EXPECT_EQ(matches.size(), 0);
    EXPECT_EQ(queue_manager->get_queue_size(), 2);
}

TEST_F(QueueManagerTest, DifferentModesDontMatch) {
    auto ranked_entry = create_entry("ranked_party", 1500);
    ranked_entry.mode = "ranked";

    auto casual_entry = create_entry("casual_party", 1500);
    casual_entry.mode = "casual";

    queue_manager->enqueue(ranked_entry);
    queue_manager->enqueue(casual_entry);

    auto matches = queue_manager->tick();

    // Should not form a match across modes
    EXPECT_EQ(matches.size(), 0);
    EXPECT_EQ(queue_manager->get_queue_size(), 2);
}

TEST_F(QueueManagerTest, TimeoutRemoval) {
    auto entry = create_entry("party1", 1500);
    entry.enqueued_at = std::chrono::system_clock::now() - std::chrono::seconds(10);

    queue_manager->enqueue(entry);
    EXPECT_EQ(queue_manager->get_queue_size(), 1);

    // Tick should remove timed-out entry
    queue_manager->tick();
    EXPECT_EQ(queue_manager->get_queue_size(), 0);
}

class TeamBuilderTest : public ::testing::Test {
protected:
    QueueEntry create_entry(const std::string& id, int mmr, int party_size = 1) {
        QueueEntry entry;
        entry.party_id = id;
        entry.region = "us-west";
        entry.mode = "ranked";
        entry.team_size = 5;
        entry.party_size = party_size;
        entry.avg_mmr = mmr;
        entry.enqueued_at = std::chrono::system_clock::now();

        for (int i = 0; i < party_size; ++i) {
            entry.player_ids.push_back(id + "_p" + std::to_string(i));
        }

        return entry;
    }
};

TEST_F(TeamBuilderTest, BasicMatchFormation) {
    std::vector<QueueEntry> entries;
    for (int i = 0; i < 10; ++i) {
        entries.push_back(create_entry("party" + std::to_string(i), 1500, 1));
    }

    auto match_opt = TeamBuilder::try_form_match(entries, 5, 2, 200);

    ASSERT_TRUE(match_opt.has_value());
    auto match = match_opt.value();

    EXPECT_EQ(match.teams.size(), 2);
    EXPECT_EQ(match.teams[0].size() + match.teams[1].size(), 10);
    EXPECT_GT(match.quality_score, 0.0);
}

TEST_F(TeamBuilderTest, InsufficientPlayers) {
    std::vector<QueueEntry> entries;
    for (int i = 0; i < 5; ++i) {  // Only 5 players, need 10
        entries.push_back(create_entry("party" + std::to_string(i), 1500, 1));
    }

    auto match_opt = TeamBuilder::try_form_match(entries, 5, 2, 200);

    EXPECT_FALSE(match_opt.has_value());
}

TEST_F(TeamBuilderTest, MMRTooWide) {
    std::vector<QueueEntry> entries;
    entries.push_back(create_entry("low", 1000, 5));
    entries.push_back(create_entry("high", 2000, 5));  // 1000 MMR difference

    auto match_opt = TeamBuilder::try_form_match(entries, 5, 2, 200);

    EXPECT_FALSE(match_opt.has_value());
}

TEST_F(TeamBuilderTest, MatchQualityScore) {
    std::vector<QueueEntry> entries;
    // Create perfectly balanced teams
    for (int i = 0; i < 10; ++i) {
        entries.push_back(create_entry("party" + std::to_string(i), 1500, 1));
    }

    auto match_opt = TeamBuilder::try_form_match(entries, 5, 2, 200);

    ASSERT_TRUE(match_opt.has_value());
    auto match = match_opt.value();

    // Quality should be high for balanced match
    EXPECT_GT(match.quality_score, 0.7);
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
