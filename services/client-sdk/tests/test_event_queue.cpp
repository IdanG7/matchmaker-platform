#include <gtest/gtest.h>
#include "matchmaker/event_queue.hpp"
#include <thread>

using namespace matchmaker;

TEST(EventQueueTest, PushAndPoll) {
    EventQueue queue;

    Event event{
        EventType::CONNECTED,
        {{"message", "test"}},
        std::chrono::system_clock::now()
    };

    queue.push(event);

    auto polled = queue.poll();
    ASSERT_TRUE(polled.has_value());
    EXPECT_EQ(polled->type, EventType::CONNECTED);
    EXPECT_EQ(polled->data["message"], "test");
}

TEST(EventQueueTest, PollEmpty) {
    EventQueue queue;

    auto polled = queue.poll();
    EXPECT_FALSE(polled.has_value());
}

TEST(EventQueueTest, Size) {
    EventQueue queue;

    EXPECT_EQ(queue.size(), 0);

    Event event{EventType::CONNECTED, {}, std::chrono::system_clock::now()};
    queue.push(event);

    EXPECT_EQ(queue.size(), 1);

    queue.push(event);
    EXPECT_EQ(queue.size(), 2);

    queue.poll();
    EXPECT_EQ(queue.size(), 1);
}

TEST(EventQueueTest, Clear) {
    EventQueue queue;

    Event event{EventType::CONNECTED, {}, std::chrono::system_clock::now()};
    queue.push(event);
    queue.push(event);
    queue.push(event);

    EXPECT_EQ(queue.size(), 3);

    queue.clear();
    EXPECT_EQ(queue.size(), 0);
}

TEST(EventQueueTest, WaitFor) {
    EventQueue queue;

    // Wait with timeout (should timeout)
    auto result = queue.wait_for(std::chrono::milliseconds(100));
    EXPECT_FALSE(result.has_value());

    // Push event and wait
    std::thread pusher([&queue]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Event event{EventType::MATCH_FOUND, {}, std::chrono::system_clock::now()};
        queue.push(event);
    });

    auto event = queue.wait_for(std::chrono::milliseconds(200));
    ASSERT_TRUE(event.has_value());
    EXPECT_EQ(event->type, EventType::MATCH_FOUND);

    pusher.join();
}

TEST(EventQueueTest, Callbacks) {
    EventQueue queue;

    bool callback_called = false;
    EventType received_type = EventType::UNKNOWN;

    queue.on(EventType::MEMBER_JOINED, [&](const Event& e) {
        callback_called = true;
        received_type = e.type;
    });

    Event event{EventType::MEMBER_JOINED, {}, std::chrono::system_clock::now()};
    queue.push(event);

    // Poll to trigger callback
    queue.poll();

    EXPECT_TRUE(callback_called);
    EXPECT_EQ(received_type, EventType::MEMBER_JOINED);
}

TEST(EventQueueTest, MultipleCallbacks) {
    EventQueue queue;

    int callback1_count = 0;
    int callback2_count = 0;

    queue.on(EventType::MEMBER_READY, [&](const Event&) { callback1_count++; });
    queue.on(EventType::MEMBER_READY, [&](const Event&) { callback2_count++; });

    Event event{EventType::MEMBER_READY, {}, std::chrono::system_clock::now()};
    queue.push(event);

    queue.poll();

    EXPECT_EQ(callback1_count, 1);
    EXPECT_EQ(callback2_count, 1);
}
