#!/usr/bin/env python3
"""Seed the database with test players and data."""

import os
import sys
import random
from datetime import datetime, timedelta, timezone

# Add parent directory to path to import common modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg2
from psycopg2.extras import execute_values
import bcrypt

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/game")
NUM_PLAYERS = 50

# Regions and modes
REGIONS = ["na-east", "na-west", "eu-west", "eu-central", "asia-east", "asia-southeast"]
PLATFORMS = ["pc", "playstation", "xbox", "switch"]
USERNAMES = [
    "Shadow", "Phoenix", "Dragon", "Viper", "Raven", "Storm", "Blaze", "Frost",
    "Thunder", "Nova", "Eclipse", "Titan", "Phantom", "Ghost", "Hunter", "Warrior",
    "Knight", "Ranger", "Mage", "Rogue", "Paladin", "Druid", "Monk", "Berserker",
    "Ninja", "Samurai", "Sniper", "Pyro", "Medic", "Scout", "Heavy", "Engineer",
    "Spy", "Demo", "Soldier", "Wizard", "Sorcerer", "Necro", "Assassin", "Archer",
    "Tank", "Healer", "DPS", "Support", "Carry", "Mid", "Jungle", "Top", "Bot", "Sup"
]


def generate_password_hash(password: str) -> str:
    """Generate bcrypt password hash."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed_database():
    """Seed the database with test data."""
    print(f"Connecting to database: {DATABASE_URL}")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("Clearing existing test data...")
        cur.execute("TRUNCATE game.player CASCADE")

        print(f"Creating {NUM_PLAYERS} test players...")

        # Generate players
        players = []
        for i in range(NUM_PLAYERS):
            username = f"{random.choice(USERNAMES)}{random.randint(100, 999)}"
            email = f"player{i+1}@test.com"
            password_hash = generate_password_hash("password123")
            region = random.choice(REGIONS)
            mmr = random.randint(800, 2000)
            platform = random.choice(PLATFORMS)

            players.append((
                email,
                password_hash,
                username,
                region,
                mmr,
                platform,
                '{}',  # metadata
            ))

        # Insert players
        execute_values(
            cur,
            """
            INSERT INTO game.player (email, password_hash, username, region, mmr, platform, metadata)
            VALUES %s
            RETURNING id
            """,
            players,
            page_size=100
        )

        player_ids = [row[0] for row in cur.fetchall()]
        print(f"✓ Created {len(player_ids)} players")

        # Create some parties
        print("Creating test parties...")
        num_parties = 10
        for i in range(num_parties):
            # Random leader from players
            leader_id = random.choice(player_ids)
            region = random.choice(REGIONS)
            size = random.randint(1, 5)

            cur.execute(
                """
                INSERT INTO game.party (leader_id, region, size, status)
                VALUES (%s, %s, %s, 'idle')
                RETURNING id
                """,
                (leader_id, region, size)
            )
            party_id = cur.fetchone()[0]

            # Add party members
            members = random.sample(player_ids, min(size, len(player_ids)))
            for member_id in members:
                cur.execute(
                    """
                    INSERT INTO game.party_member (party_id, player_id, ready)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (party_id, member_id, random.choice([True, False]))
                )

        print(f"✓ Created {num_parties} parties")

        # Create some historical matches
        print("Creating match history...")
        num_matches = 20
        for i in range(num_matches):
            mode = random.choice(["ranked", "casual", "tournament"])
            region = random.choice(REGIONS)
            mmr_avg = random.randint(1000, 1800)
            status = "ended"

            # Create match
            cur.execute(
                """
                INSERT INTO game.match (mode, region, mmr_avg, status, server_endpoint, created_at, started_at, ended_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    mode,
                    region,
                    mmr_avg,
                    status,
                    f"udp://10.0.0.{random.randint(1, 255)}:30000",
                    datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
                    datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
                    datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
                )
            )
            match_id = cur.fetchone()[0]

            # Add 10 players (5v5)
            match_players = random.sample(player_ids, min(10, len(player_ids)))
            for idx, player_id in enumerate(match_players):
                team = 0 if idx < 5 else 1
                result = "win" if (team == 0 and random.random() > 0.5) or (team == 1 and random.random() <= 0.5) else "loss"
                mmr_change = random.randint(-25, 25)

                # Get player MMR
                cur.execute("SELECT mmr FROM game.player WHERE id = %s", (player_id,))
                mmr_before = cur.fetchone()[0]
                mmr_after = mmr_before + mmr_change

                # Insert match player
                cur.execute(
                    """
                    INSERT INTO game.match_player (match_id, player_id, team, mmr_before, mmr_after, result)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (match_id, player_id, team, mmr_before, mmr_after, result)
                )

                # Insert match history
                cur.execute(
                    """
                    INSERT INTO game.match_history (match_id, player_id, mode, result, mmr_change, team)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (match_id, player_id, mode, result, mmr_change, team)
                )

        print(f"✓ Created {num_matches} historical matches")

        # Update leaderboard
        print("Updating leaderboard...")
        cur.execute(
            """
            INSERT INTO game.leaderboard (season, player_id, rating, games_played, wins, losses)
            SELECT
                '2025-q4',
                p.id,
                p.mmr,
                COUNT(mh.id),
                COUNT(CASE WHEN mh.result = 'win' THEN 1 END),
                COUNT(CASE WHEN mh.result = 'loss' THEN 1 END)
            FROM game.player p
            LEFT JOIN game.match_history mh ON mh.player_id = p.id
            GROUP BY p.id, p.mmr
            ON CONFLICT (season, player_id) DO UPDATE
            SET rating = EXCLUDED.rating,
                games_played = EXCLUDED.games_played,
                wins = EXCLUDED.wins,
                losses = EXCLUDED.losses
            """
        )

        # Update ranks
        cur.execute("SELECT game.update_leaderboard_ranks('2025-q4')")
        print("✓ Updated leaderboard rankings")

        conn.commit()
        cur.close()
        conn.close()

        print("\n✅ Database seeded successfully!")
        print(f"\nTest credentials:")
        print(f"  Email: player1@test.com (or player2@test.com, etc.)")
        print(f"  Password: password123")

    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
