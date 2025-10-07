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

## API Endpoints

The API service is running at `http://localhost:8080`

**Authentication** (Phase 2):
- `POST /v1/auth/register` - Register new user
- `POST /v1/auth/login` - Login and get JWT tokens
- `POST /v1/auth/refresh` - Refresh access token

**Profile** (Phase 2):
- `GET /v1/profile/me` - Get authenticated user profile (requires JWT)
- `PATCH /v1/profile/me` - Update user profile (requires JWT)

**Party/Lobby** (Phase 3):
- `POST /v1/party` - Create a new party
- `GET /v1/party/{id}` - Get party details
- `POST /v1/party/{id}/join` - Join a party
- `DELETE /v1/party/{id}/leave` - Leave a party
- `POST /v1/party/{id}/ready` - Toggle ready status
- `POST /v1/party/queue` - Enter matchmaking queue
- `DELETE /v1/party/queue` - Leave matchmaking queue
- `WS /v1/ws/party/{party_id}` - WebSocket for real-time party updates

**Session** (Phase 5):
- `GET /v1/session/{match_id}` - Get session details (server endpoint + token)
- `POST /v1/session/{match_id}/heartbeat` - Game server heartbeat
- `POST /v1/session/{match_id}/result` - Submit match result

**Leaderboard & Match History** (Phase 6):
- `GET /v1/matches/history` - Get match history (paginated, filterable by player/mode)
- `GET /v1/leaderboard/{season}` - Get leaderboard for specific season
- `GET /v1/leaderboard` - Get current season leaderboard

**Documentation**:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Development Phases

- [x] Phase 0: Repository Structure & Foundation
- [x] Phase 1: Database & Core Infrastructure
- [x] Phase 2: Auth & Profile Service
- [x] Phase 3: Lobby/Party Service
- [x] Phase 4: Matchmaker Core (C++)
- [x] Phase 5: Session Service
- [x] Phase 6: Leaderboard & Match History
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
