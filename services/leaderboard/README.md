# Leaderboard & Match History Service

Rankings and historical match data.

## Responsibilities

- Append-only match history storage
- Seasonal and global leaderboards
- Top-N queries with pagination
- Async leaderboard recalculations

## Implementation Status

- [ ] Phase 6: Match history storage
- [ ] Phase 6: Leaderboard queries
- [ ] Phase 6: Seasonal rankings
- [ ] Async recalculation via NATS

## Running

```bash
# Development
python main.py

# With Docker
docker compose up leaderboard
```
