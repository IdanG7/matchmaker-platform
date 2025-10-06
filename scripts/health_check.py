#!/usr/bin/env python3
"""Health check script for infrastructure services."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import psycopg2
import redis
from nats.aio.client import Client as NATS


def check_postgres():
    """Check PostgreSQL connection."""
    try:
        DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql://postgres:password@localhost:5432/game"
        )
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        print("✅ PostgreSQL: OK")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: FAILED - {e}")
        return False


def check_redis():
    """Check Redis connection."""
    try:
        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        r.close()
        print("✅ Redis: OK")
        return True
    except Exception as e:
        print(f"❌ Redis: FAILED - {e}")
        return False


async def check_nats():
    """Check NATS connection."""
    try:
        NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
        nc = NATS()
        await nc.connect(servers=[NATS_URL])
        await nc.close()
        print("✅ NATS: OK")
        return True
    except Exception as e:
        print(f"❌ NATS: FAILED - {e}")
        return False


async def main():
    """Run all health checks."""
    print("Running infrastructure health checks...\n")

    results = [
        check_postgres(),
        check_redis(),
        await check_nats(),
    ]

    print("\n" + "=" * 50)
    if all(results):
        print("✅ All infrastructure services are healthy!")
        sys.exit(0)
    else:
        print("❌ Some infrastructure services are unhealthy!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
