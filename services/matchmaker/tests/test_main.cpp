#include <gtest/gtest.h>
#include "matchmaker/queue_manager.hpp"
#include "matchmaker/team_builder.hpp"

#include <chrono>
#include <string>
#include <vector>

using namespace matchmaker;

namespace {

QueueEntry make_entry(const std::string& party_id,
                      const std::string& region,
                      const std::string& mode,
                      int team_size,
                      int avg_mmr,
                      int party_size = 1) {
    QueueEntry e;
    e.party_id = party_id;
    e.region = region;
    e.mode = mode;
    e.team_size = team_size;
    e.party_size = party_size;
    e.avg_mmr = avg_mmr;
    e.enqueued_at = std::chrono::system_clock::now();
    for (int i = 0; i < party_size; ++i) {
        e.player_ids.push_back(party_id + "-p" + std::to_string(i));
    }
    return e;
}

}  // namespace

TEST(QueueManagerTest, EnqueueAndIsQueued) {
    QueueManager qm;
    auto e = make_entry("party-1", "us-east", "ranked", 1, 1500);

    EXPECT_FALSE(qm.is_queued("party-1"));
    qm.enqueue(e);
    EXPECT_TRUE(qm.is_queued("party-1"));
    EXPECT_EQ(qm.get_queue_size(), 1u);
}

TEST(QueueManagerTest, DequeueRemovesParty) {
    QueueManager qm;
    qm.enqueue(make_entry("party-1", "us-east", "ranked", 1, 1500));
    qm.enqueue(make_entry("party-2", "us-east", "ranked", 1, 1520));
    EXPECT_EQ(qm.get_queue_size(), 2u);

    qm.dequeue("party-1");
    EXPECT_FALSE(qm.is_queued("party-1"));
    EXPECT_TRUE(qm.is_queued("party-2"));
    EXPECT_EQ(qm.get_queue_size(), 1u);
}

TEST(QueueManagerTest, BucketsSeparateByRegion) {
    QueueManager qm;
    qm.enqueue(make_entry("p-us", "us-east", "ranked", 1, 1500));
    qm.enqueue(make_entry("p-eu", "eu-west", "ranked", 1, 1500));

    auto sizes = qm.get_bucket_sizes();
    EXPECT_EQ(sizes.size(), 2u);
}

TEST(TeamBuilderTest, FormsBalancedTwoTeamMatch) {
    std::vector<QueueEntry> entries = {
        make_entry("p1", "us-east", "ranked", 2, 1500),
        make_entry("p2", "us-east", "ranked", 2, 1510),
        make_entry("p3", "us-east", "ranked", 2, 1490),
        make_entry("p4", "us-east", "ranked", 2, 1505),
    };

    auto match = TeamBuilder::try_form_match(entries, /*team_size=*/2,
                                              /*num_teams=*/2, /*mmr_tolerance=*/200);
    ASSERT_TRUE(match.has_value());
    EXPECT_EQ(match->teams.size(), 2u);
    EXPECT_EQ(match->teams[0].size(), 2u);
    EXPECT_EQ(match->teams[1].size(), 2u);
}

TEST(TeamBuilderTest, ReturnsNulloptWhenNotEnoughPlayers) {
    std::vector<QueueEntry> entries = {
        make_entry("p1", "us-east", "ranked", 2, 1500),
        make_entry("p2", "us-east", "ranked", 2, 1510),
    };

    auto match = TeamBuilder::try_form_match(entries, 2, 2, 200);
    EXPECT_FALSE(match.has_value());
}

TEST(TeamBuilderTest, RespectsMmrTolerance) {
    std::vector<QueueEntry> entries = {
        make_entry("p1", "us-east", "ranked", 1, 1000),
        make_entry("p2", "us-east", "ranked", 1, 3000),
    };

    auto match = TeamBuilder::try_form_match(entries, 1, 2, /*mmr_tolerance=*/100);
    EXPECT_FALSE(match.has_value());
}
