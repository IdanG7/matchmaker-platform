-- Initial schema for Multiplayer Matchmaking Platform
-- Phase 1: Database & Core Infrastructure

-- Create schema
CREATE SCHEMA IF NOT EXISTS game;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PLAYERS
-- ============================================================================

CREATE TABLE game.player (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    region TEXT NOT NULL,
    mmr INT NOT NULL DEFAULT 1200,
    banned BOOLEAN NOT NULL DEFAULT FALSE,
    ban_reason TEXT,
    banned_until TIMESTAMPTZ,
    platform TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_player_email ON game.player(email);
CREATE INDEX idx_player_username ON game.player(username);
CREATE INDEX idx_player_region ON game.player(region);
CREATE INDEX idx_player_mmr ON game.player(mmr);
CREATE INDEX idx_player_banned ON game.player(banned) WHERE banned = TRUE;

-- ============================================================================
-- PARTIES / LOBBIES
-- ============================================================================

CREATE TABLE game.party (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    leader_id UUID NOT NULL REFERENCES game.player(id) ON DELETE CASCADE,
    region TEXT NOT NULL,
    size INT NOT NULL DEFAULT 1,
    max_size INT NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'queueing', 'ready', 'in_match', 'disbanded')),
    queue_mode TEXT,
    team_size INT,
    avg_mmr INT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_party_leader ON game.party(leader_id);
CREATE INDEX idx_party_status ON game.party(status);
CREATE INDEX idx_party_region ON game.party(region);

CREATE TABLE game.party_member (
    party_id UUID NOT NULL REFERENCES game.party(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES game.player(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ready BOOLEAN NOT NULL DEFAULT FALSE,
    role TEXT,
    PRIMARY KEY (party_id, player_id)
);

CREATE INDEX idx_party_member_player ON game.party_member(player_id);

-- ============================================================================
-- MATCHES
-- ============================================================================

CREATE TABLE game.match (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    mode TEXT NOT NULL,
    region TEXT NOT NULL,
    mmr_avg INT,
    mmr_range INT,
    server_endpoint TEXT,
    server_token TEXT,
    status TEXT NOT NULL DEFAULT 'allocating' CHECK (status IN ('allocating', 'active', 'ended', 'cancelled')),
    result JSONB,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_match_status ON game.match(status);
CREATE INDEX idx_match_region ON game.match(region);
CREATE INDEX idx_match_mode ON game.match(mode);
CREATE INDEX idx_match_created_at ON game.match(created_at DESC);

CREATE TABLE game.match_player (
    match_id UUID NOT NULL REFERENCES game.match(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES game.player(id) ON DELETE CASCADE,
    team SMALLINT NOT NULL,
    mmr_before INT NOT NULL,
    mmr_after INT,
    result TEXT CHECK (result IN ('win', 'loss', 'draw')),
    stats JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (match_id, player_id)
);

CREATE INDEX idx_match_player_player ON game.match_player(player_id);
CREATE INDEX idx_match_player_team ON game.match_player(match_id, team);

-- ============================================================================
-- LEADERBOARDS
-- ============================================================================

CREATE TABLE game.leaderboard (
    season TEXT NOT NULL,
    player_id UUID NOT NULL REFERENCES game.player(id) ON DELETE CASCADE,
    rating INT NOT NULL,
    rank INT,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    games_played INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (season, player_id)
);

CREATE INDEX idx_leaderboard_season_rating ON game.leaderboard(season, rating DESC);
CREATE INDEX idx_leaderboard_season_rank ON game.leaderboard(season, rank);
CREATE INDEX idx_leaderboard_player ON game.leaderboard(player_id);

-- ============================================================================
-- MATCH HISTORY
-- ============================================================================

CREATE TABLE game.match_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES game.match(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES game.player(id) ON DELETE CASCADE,
    played_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    mode TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
    mmr_change INT NOT NULL DEFAULT 0,
    team SMALLINT NOT NULL,
    stats JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_match_history_player ON game.match_history(player_id, played_at DESC);
CREATE INDEX idx_match_history_match ON game.match_history(match_id);
CREATE INDEX idx_match_history_mode ON game.match_history(mode);

-- ============================================================================
-- SESSIONS
-- ============================================================================

CREATE TABLE game.session (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES game.match(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'allocating' CHECK (status IN ('allocating', 'active', 'ended', 'failed')),
    server_endpoint TEXT,
    server_token TEXT,
    heartbeat_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_session_match ON game.session(match_id);
CREATE INDEX idx_session_status ON game.session(status);
CREATE INDEX idx_session_heartbeat ON game.session(heartbeat_at) WHERE status = 'active';

-- ============================================================================
-- QUEUE HISTORY (for analytics)
-- ============================================================================

CREATE TABLE game.queue_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES game.player(id) ON DELETE CASCADE,
    party_id UUID REFERENCES game.party(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('enqueue', 'dequeue', 'match_found', 'timeout')),
    mode TEXT NOT NULL,
    region TEXT NOT NULL,
    mmr INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    wait_time_ms INT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_queue_event_player ON game.queue_event(player_id, created_at DESC);
CREATE INDEX idx_queue_event_type ON game.queue_event(event_type);
CREATE INDEX idx_queue_event_created_at ON game.queue_event(created_at DESC);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_player_updated_at BEFORE UPDATE ON game.player
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_party_updated_at BEFORE UPDATE ON game.party
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCTIONS FOR LEADERBOARD MANAGEMENT
-- ============================================================================

CREATE OR REPLACE FUNCTION game.update_leaderboard_ranks(p_season TEXT)
RETURNS void AS $$
BEGIN
    WITH ranked AS (
        SELECT
            player_id,
            ROW_NUMBER() OVER (ORDER BY rating DESC) as new_rank
        FROM game.leaderboard
        WHERE season = p_season
    )
    UPDATE game.leaderboard lb
    SET rank = r.new_rank
    FROM ranked r
    WHERE lb.season = p_season
      AND lb.player_id = r.player_id
      AND (lb.rank IS NULL OR lb.rank != r.new_rank);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Create current season
INSERT INTO game.leaderboard (season, player_id, rating, rank)
SELECT '2025-q4', id, mmr, NULL
FROM game.player
ON CONFLICT DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database schema initialized successfully!';
    RAISE NOTICE 'Tables created: player, party, party_member, match, match_player, leaderboard, match_history, session, queue_event';
END $$;
