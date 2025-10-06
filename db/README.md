# Database Schema

PostgreSQL database schema for the multiplayer matchmaking platform.

## Schema: `game`

### Tables

#### `player`
Player accounts and profiles.

- **id**: UUID primary key
- **email**: Unique email address
- **password_hash**: bcrypt password hash
- **username**: Unique display name
- **region**: Geographic region (na-east, eu-west, etc.)
- **mmr**: Match making rating (default: 1200)
- **banned**: Ban status
- **platform**: Gaming platform (pc, playstation, xbox, switch)
- **metadata**: Additional player data (JSONB)

#### `party`
Lobby/party system for grouped players.

- **id**: UUID primary key
- **leader_id**: Party leader (references player)
- **region**: Party region
- **size**: Current party size
- **max_size**: Maximum party size
- **status**: idle | queueing | ready | in_match | disbanded
- **avg_mmr**: Average party MMR

#### `party_member`
Players in a party.

- **party_id**: Reference to party
- **player_id**: Reference to player
- **ready**: Ready check status
- **role**: Optional player role

#### `match`
Game matches.

- **id**: UUID primary key
- **mode**: Game mode (ranked, casual, tournament)
- **region**: Match region
- **mmr_avg**: Average match MMR
- **server_endpoint**: Game server address
- **status**: allocating | active | ended | cancelled

#### `match_player`
Players in a match.

- **match_id**: Reference to match
- **player_id**: Reference to player
- **team**: Team number (0 or 1)
- **mmr_before**: MMR before match
- **mmr_after**: MMR after match
- **result**: win | loss | draw

#### `leaderboard`
Seasonal rankings.

- **season**: Season identifier (e.g., 2025-q4)
- **player_id**: Reference to player
- **rating**: Current rating
- **rank**: Global rank
- **wins/losses/games_played**: Statistics

#### `match_history`
Historical match records per player.

- **match_id**: Reference to match
- **player_id**: Reference to player
- **played_at**: Match timestamp
- **result**: Match outcome
- **mmr_change**: MMR delta

#### `session`
Game server sessions.

- **match_id**: Reference to match
- **status**: allocating | active | ended | failed
- **server_endpoint**: Server address
- **server_token**: Authentication token
- **heartbeat_at**: Last heartbeat timestamp

#### `queue_event`
Matchmaking queue analytics.

- **player_id**: Reference to player
- **event_type**: enqueue | dequeue | match_found | timeout
- **wait_time_ms**: Time in queue
- **metadata**: Additional event data

## Functions

### `update_leaderboard_ranks(season)`
Recalculates and updates ranks for a given season.

```sql
SELECT game.update_leaderboard_ranks('2025-q4');
```

## Migrations

### Running Migrations

```bash
# Via Docker Compose
docker compose exec postgres psql -U postgres -d game -f /migrations/init.sql

# Via make
make up  # Automatically runs migrations
```

### Creating New Migrations

1. Create a new SQL file in `db/migrations/`
2. Name format: `YYYYMMDD_description.sql`
3. Include rollback statements if needed

Example:
```sql
-- 20250107_add_player_stats.sql
ALTER TABLE game.player ADD COLUMN stats JSONB DEFAULT '{}'::jsonb;
```

## Indexes

Performance indexes are created on:
- Player lookups (email, username, region, MMR)
- Match queries (status, region, mode)
- Leaderboard rankings (season + rating)
- Match history (player_id + played_at)

## Seeding Data

```bash
# Seed with 50 test players and historical data
make seed

# Test credentials
# Email: player1@test.com (or player2@test.com, etc.)
# Password: password123
```

## Querying Examples

### Top 10 Leaderboard
```sql
SELECT p.username, l.rating, l.rank, l.wins, l.losses
FROM game.leaderboard l
JOIN game.player p ON l.player_id = p.id
WHERE l.season = '2025-q4'
ORDER BY l.rank
LIMIT 10;
```

### Player Match History
```sql
SELECT m.mode, mh.result, mh.mmr_change, mh.played_at
FROM game.match_history mh
JOIN game.match m ON mh.match_id = m.id
WHERE mh.player_id = 'player-uuid'
ORDER BY mh.played_at DESC
LIMIT 20;
```

### Active Parties
```sql
SELECT p.id, pl.username as leader, p.size, p.region, p.status
FROM game.party p
JOIN game.player pl ON p.leader_id = pl.id
WHERE p.status IN ('idle', 'queueing', 'ready');
```
