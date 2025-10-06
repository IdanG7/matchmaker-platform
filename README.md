# Distributed Multiplayer Matchmaking & Game Services Platform

A production-grade matchmaking and game services platform built with C++ and Python microservices.

## Tech Stack

- **Matchmaker Core**: C++ (high-performance tick-based matching)
- **Services**: Python (FastAPI microservices)
- **Message Bus**: NATS
- **Cache/Queues**: Redis
- **Database**: PostgreSQL
- **Observability**: OpenTelemetry, Prometheus, Grafana, Jaeger
- **Container Orchestration**: Docker Compose (dev), Kubernetes (prod-ready)

## Architecture

```
Client SDK (C++) <-> Gateway API (FastAPI) <-> Services (NATS RPC)
                                           <-> Matchmaker Core (C++)
                                           <-> Redis (queues/cache)
                                           <-> PostgreSQL (persistent state)
```

## Services

- **Gateway API**: REST & WebSocket endpoints, JWT validation, rate limiting
- **Matchmaker**: High-performance C++ core with region/MMR/latency constraints
- **Lobby**: Party management, ready checks, chat rooms
- **Session**: Game server allocation and lifecycle management
- **Profile**: Player identities, MMR, regions, preferences
- **Leaderboard**: Match history, seasonal rankings

## Quick Start

```bash
# Start all services
make up

# View logs
make logs

# Run tests
make test

# Seed test data
make seed

# Stop all services
make down
```

## Development Phases

- [x] Phase 0: Repository Structure & Foundation
- [x] Phase 1: Database & Core Infrastructure
- [ ] Phase 2: Auth & Profile Service
- [ ] Phase 3: Lobby/Party Service
- [ ] Phase 4: Matchmaker Core (C++)
- [ ] Phase 5: Session Service
- [ ] Phase 6: Leaderboard & Match History
- [ ] Phase 7: Client SDK (C++)
- [ ] Phase 8: Observability & Testing

## Project Structure

```
services/           # Microservices
  api/             # FastAPI gateway
  matchmaker/      # C++ matchmaking core
  lobby/           # Party/lobby management
  session/         # Game session allocation
  profile/         # Player profiles
  leaderboard/     # Rankings & history
sdk/               # Client SDKs
  cpp/             # C++ game client SDK
  python/          # Python SDK (testing/tools)
deployments/       # Deployment configs
  docker/          # Docker Compose
  k8s/             # Kubernetes manifests
db/                # Database migrations
ops/               # Observability configs
tests/             # Integration & load tests
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT
