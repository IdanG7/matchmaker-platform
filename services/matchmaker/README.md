# Matchmaker Service (C++)

High-performance matchmaking engine for multiplayer games.

## Overview

The matchmaker service is responsible for:
- Consuming queue events from NATS (published by the Party service)
- Grouping players into buckets by region/mode/team size
- Forming balanced teams using MMR-based algorithms
- Publishing match found events back to NATS
- Exporting metrics to Prometheus

## Architecture

### Components

**QueueManager** (`queue_manager.hpp/cpp`)
- Manages matchmaking queues organized by bucket (region + mode + team_size)
- Implements MMR band widening over time
- Processes queues each tick to form matches
- Removes timed-out entries

**TeamBuilder** (`team_builder.hpp/cpp`)
- Team formation algorithms
- Greedy MMR balancing
- Match quality scoring (0-1)
- Validates MMR tolerance constraints

**NatsClient** (`nats_client.hpp`)
- Interface for pub/sub messaging
- Mock implementation for testing
- Subscribes to `matchmaker.queue.*` subjects
- Publishes `match.found` events

### Matchmaking Algorithm

1. **Bucket Organization**: Parties are grouped by `(region, mode, team_size)` to ensure only compatible matches are attempted

2. **MMR Band Widening**:
   ```
   band = initial_band + (wait_time_seconds * growth_rate)
   band = min(band, max_band)

   Default: 100 + (t * 10), capped at 500
   ```

3. **Team Formation**:
   - Sort parties by wait time (fairness)
   - For longest-waiting party, calculate current MMR tolerance
   - Attempt to form teams using greedy MMR balancing
   - Validate match quality > threshold

4. **Quality Scoring**:
   - MMR balance between teams (50% weight)
   - MMR variance within match (30% weight)
   - Wait time fairness (20% weight)

5. **Match Publishing**:
   - Matched parties removed from queue
   - Match details published to NATS
   - Session service allocates game server

## Configuration

```cpp
QueueConfig {
    mmr_band_initial = 100;           // Initial ±MMR range
    mmr_band_max = 500;               // Maximum ±MMR range
    mmr_band_growth_per_sec = 10;     // MMR widening rate
    max_wait_time_sec = 120;          // Queue timeout
    min_match_quality = 0.6;          // Min quality threshold
}
```

## Building

### Prerequisites

- CMake 3.20+
- C++20 compiler (GCC 11+, Clang 14+, MSVC 2022+)
- spdlog (via vcpkg)
- nlohmann/json (via vcpkg)

### Build Commands

```bash
cd services/matchmaker
mkdir build && cd build

# Configure
cmake .. -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]/scripts/buildsystems/vcpkg.cmake

# Build
cmake --build .

# Run tests
ctest --verbose
```

## Running

```bash
./matchmaker
```

The service will:
- Connect to NATS (mock mode by default)
- Subscribe to queue events
- Process queues every 200ms
- Log stats every 10 seconds

## Testing

Run unit tests:
```bash
cd build
./matchmaker_tests
```

Tests cover:
- Queue enqueue/dequeue operations
- Match formation logic
- MMR band widening
- Bucket isolation (region/mode)
- Party size handling
- Timeout removal
- Team balancing
- Quality scoring

## Performance

**Target Metrics** (Phase 4 Success Criteria):
- Tick latency: < 10ms p99
- Memory: O(n) where n = queued parties
- Match quality: > 0.6 average
- No cross-region/mode matches

**Current Status**:
- ✅ Core algorithms implemented
- ✅ Unit tests passing
- ⏳ Benchmarking (Phase 8)
- ⏳ Load testing with 1000+ queues (Phase 8)

## Future Enhancements

- [ ] Redis integration for persistent queue state
- [ ] Real NATS client (nats.c)
- [ ] Prometheus metrics export
- [ ] Backfill queue handling
- [ ] Advanced algorithms (skill-based roles, latency-aware matching)
- [ ] Dynamic MMR tuning based on queue depth
- [ ] Multi-region fallback

## API

### Queue Event Format (NATS Input)

```json
{
  "party_id": "uuid",
  "region": "us-west",
  "mode": "ranked",
  "team_size": 5,
  "party_size": 3,
  "avg_mmr": 1500,
  "player_ids": ["p1", "p2", "p3"],
  "enqueued_at": "2025-01-01T00:00:00Z"
}
```

### Match Found Event (NATS Output)

```json
{
  "match_id": "match_abc123",
  "region": "us-west",
  "mode": "ranked",
  "team_size": 5,
  "teams": [
    ["p1", "p2", "p3", "p4", "p5"],
    ["p6", "p7", "p8", "p9", "p10"]
  ],
  "party_ids": ["party1", "party2", ...],
  "avg_mmr": 1520,
  "mmr_variance": 45,
  "quality_score": 0.87
}
```

## License

See root LICENSE file.
