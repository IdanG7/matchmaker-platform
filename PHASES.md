# Development Phases

This document outlines the phased implementation plan for the Multiplayer Matchmaking Platform.

---

## Phase 0: Repository Structure & Foundation ✅

**Status**: Complete

**Deliverables**:
- [x] Repository structure with all directories
- [x] Docker Compose infrastructure setup
- [x] Makefile for common operations
- [x] CI/CD pipeline (GitHub Actions)
- [x] C++ project scaffolding (CMake)
- [x] Documentation (README, CONTRIBUTING)

**Outcome**: Development environment ready for implementation.

---

## Phase 1: Database & Core Infrastructure ✅

**Status**: Complete

**Duration**: Completed

**Goals**:
- Set up PostgreSQL schema ✅
- Create database migration system ✅
- Establish Redis and NATS connectivity ✅
- Health check endpoints for all infrastructure ✅

**Tasks**:
- [x] Write SQL schema (`db/migrations/init.sql`)
- [x] Create database migration system
- [x] Implement Redis connection pool helper
- [x] Implement NATS client wrapper
- [x] Add infrastructure health check script
- [x] Seed script for test data

**Deliverables**:
- ✅ PostgreSQL schema with 9 tables (player, party, match, leaderboard, etc.)
- ✅ Redis client helper (`services/common/infra/redis_client.py`)
- ✅ NATS client wrapper (`services/common/infra/nats_client.py`)
- ✅ Database connection manager (`services/common/infra/database.py`)
- ✅ Seed script with 50 test players, 10 parties, 20 matches
- ✅ Health check script for all infrastructure

**Success Criteria**:
- ✅ `make up` successfully starts all infrastructure
- ✅ Database schema created with migrations
- ✅ Seed data loads successfully (50 players, 10 parties, 20 matches)
- ✅ Leaderboard rankings calculated correctly

---

## Phase 2: Auth & Profile Service ✅

**Status**: Complete

**Duration**: Completed

**Goals**:
- JWT-based authentication ✅
- User registration and login ✅
- Profile management ✅
- Rate limiting ✅

**Tasks**:
- [x] Implement password hashing (bcrypt)
- [x] JWT token generation and validation
- [x] `POST /v1/auth/register` endpoint
- [x] `POST /v1/auth/login` endpoint
- [x] `POST /v1/auth/refresh` endpoint
- [x] `GET /v1/profile/me` endpoint
- [x] `PATCH /v1/profile/me` endpoint
- [x] Redis-based rate limiting
- [ ] Profile service NATS handlers (deferred to Phase 3)
- [x] Unit tests for auth flows

**Deliverables**:
- ✅ FastAPI application with proper structure (routes, models, middleware)
- ✅ User registration with bcrypt password hashing
- ✅ JWT-based authentication (access + refresh tokens)
- ✅ Profile GET and PATCH endpoints with JWT auth
- ✅ Redis-based rate limiting middleware (60 req/min per IP)
- ✅ Unit tests for authentication utilities
- ✅ Dockerized API service running on port 8080
- ✅ API documentation at /docs endpoint

**Success Criteria**:
- ✅ Users can register and login
- ✅ JWT tokens issued and validated
- ✅ Profile CRUD operations work
- ✅ Rate limiting prevents abuse
- ✅ Unit tests for auth utilities pass

---

## Phase 3: Lobby/Party Service ✅

**Status**: Complete

**Duration**: Completed

**Goals**:
- Party creation and management ✅
- Ready check system ✅
- Integration with matchmaking queue ✅

**Tasks**:
- [x] `POST /v1/party` - Create party
- [x] `POST /v1/party/{id}/join` - Join party
- [x] `POST /v1/party/{id}/leave` - Leave party
- [x] `POST /v1/party/{id}/ready` - Ready check
- [x] `POST /v1/party/queue` - Enter matchmaking queue
- [x] `DELETE /v1/party/queue` - Leave matchmaking queue
- [x] `GET /v1/party/{id}` - Get party details
- [x] WebSocket lobby events (`/v1/ws/party/{party_id}`)
- [x] Redis party state management
- [x] NATS integration for queue events
- [x] Unit and integration tests

**Deliverables**:
- ✅ Party CRUD endpoints with JWT authentication
- ✅ WebSocket real-time updates (member_joined, member_left, member_ready, queue_entered, queue_left)
- ✅ Redis caching with graceful degradation
- ✅ NATS event publishing to matchmaker (`matchmaker.queue.{mode}.{region}`)
- ✅ Party lifecycle FSM (idle → queueing → ready → in_match → disbanded)
- ✅ 26 comprehensive unit tests - all passing

**Success Criteria**:
- ✅ Players can create/join/leave parties
- ✅ Ready check works correctly
- ✅ Party state synced via WebSocket
- ✅ Queue events published to matchmaker

---

## Phase 4: Matchmaker Core (C++) ✅

**Status**: Complete

**Duration**: Completed

**Goals**:
- High-performance tick-based matchmaking ✅
- Region/MMR/latency constraints ✅
- Team formation algorithm ✅
- Backfill support (deferred to post-MVP)

**Tasks**:
- [x] NATS client interface (mock implementation for testing)
- [x] Queue bucket management (region/mode/team_size)
- [x] MMR band calculation with time-based widening
- [x] Team formation algorithm (greedy MMR balancing)
- [x] Match quality scoring (balance + variance + fairness)
- [x] Timeout removal for stale queue entries
- [x] Main tick loop with 200ms intervals
- [x] Unit tests with mocked Redis/NATS (11 tests, all passing)
- [ ] Redis client integration (hiredis) - deferred
- [ ] Real NATS client integration (nats.c) - deferred
- [ ] Backfill queue handling - deferred
- [ ] Prometheus metrics export - deferred to Phase 8
- [ ] Load testing (1000+ concurrent queues) - deferred to Phase 8

**Deliverables**:
- ✅ QueueManager with bucket isolation (region + mode + team_size)
- ✅ MMR band widening algorithm (100 → 500 over 40 seconds)
- ✅ TeamBuilder with greedy balancing and quality scoring
- ✅ Match quality calculation (0-1 scale)
- ✅ Mock NATS client interface for testing
- ✅ Comprehensive test suite (11 tests covering queue ops, matching, isolation)
- ✅ Main service with tick-based processing
- ✅ README with architecture documentation

**Success Criteria**:
- ✅ Correct team formation (balanced MMR)
- ✅ Queue bucket isolation (no cross-region/mode matches)
- ✅ MMR tolerance respects time-based widening
- ✅ Match quality scoring implemented
- ✅ All unit tests passing (11/11)

---

## Phase 5: Session Service ✅

**Status**: Complete

**Duration**: Completed

**Goals**:
- Game session allocation ✅
- Lifecycle management ✅
- Server endpoint distribution ✅

**Tasks**:
- [x] Mock server allocator (returns static endpoint)
- [x] Session lifecycle FSM (allocating → active → ended → cancelled)
- [x] `GET /v1/session/{match_id}` endpoint
- [x] `POST /v1/session/{match_id}/heartbeat` endpoint
- [x] `POST /v1/session/{match_id}/result` endpoint
- [x] Session token generation (HMAC-SHA256)
- [x] Heartbeat tracking with Redis TTL (30s)
- [x] Match result writeback to database
- [x] NATS event consumer for match.found events
- [x] Unit tests for lifecycle and endpoints

**Deliverables**:
- ✅ NATS consumer for `match.found` events (auto-allocates sessions)
- ✅ MockServerAllocator (returns `region.game.example.com:port`)
- ✅ HMAC-SHA256 session token generation and verification
- ✅ SessionLifecycleManager FSM with state validation
- ✅ Redis-based heartbeat tracking (30s TTL)
- ✅ Session endpoints: GET details, POST heartbeat, POST result
- ✅ Match result persistence (winner team, player stats, duration)
- ✅ Party status updates (in_match → idle)
- ✅ 22 comprehensive unit tests - all passing

**Success Criteria**:
- ✅ Sessions allocated when match found
- ✅ Players receive server endpoint + token
- ✅ Heartbeats tracked correctly
- ✅ Match results persisted
- ✅ Timeouts handled gracefully

---

## Phase 6: Leaderboard & Match History ✅

**Status**: Complete

**Duration**: Completed

**Goals**:
- Persistent match history ✅
- Seasonal leaderboards ✅
- Efficient top-N queries ✅

**Tasks**:
- [x] Match history table schema (already in DB)
- [x] `GET /v1/matches/history` endpoint (paginated, filterable)
- [x] `GET /v1/leaderboard/{season}` endpoint
- [x] `GET /v1/leaderboard` endpoint (current season)
- [x] MMR calculation (Elo-based with K=32)
- [x] Automatic leaderboard updates on match completion
- [x] Database indexes for efficient queries
- [x] Unit tests for ranking logic and endpoints

**Deliverables**:
- ✅ Match history endpoint with pagination and mode filtering
- ✅ Leaderboard endpoints for specific or current season
- ✅ Elo-based MMR calculation (K-factor 32)
- ✅ Automatic match_history insertion on match end
- ✅ Automatic leaderboard upsert with wins/losses/rating
- ✅ Player MMR updates after each match
- ✅ Leaderboard sorted by rating DESC
- ✅ Win rate calculation in leaderboard entries
- ✅ 15 comprehensive unit tests covering history, leaderboard, MMR

**Success Criteria**:
- ✅ Match history queryable by player
- ✅ Leaderboard queries optimized with indexes
- ✅ Seasonal rankings update correctly
- ✅ MMR changes reflected in player stats and leaderboard

---

## Phase 7: Client SDK (C++)

**Duration**: ~5-7 days

**Goals**:
- Easy-to-use C++ SDK for game clients
- REST and WebSocket support
- Event callbacks

**Tasks**:
- [ ] HTTP client (libcurl or httplib)
- [ ] WebSocket client (ixwebsocket or Boost.Beast)
- [ ] Auth API wrapper
- [ ] Profile API wrapper
- [ ] Party/lobby API wrapper
- [ ] Matchmaking API wrapper
- [ ] Event callback system
- [ ] Thread-safe event queue
- [ ] Example client application
- [ ] Unit tests and integration tests

**Success Criteria**:
- SDK builds on Linux/macOS/Windows
- Simple API for common operations
- WebSocket events delivered reliably
- Example client demonstrates full flow
- Comprehensive documentation

---

## Phase 8: Observability & Testing

**Duration**: ~4-6 days

**Goals**:
- Production-ready observability
- Load and chaos testing
- SLO monitoring

**Tasks**:
- [ ] OpenTelemetry traces end-to-end
- [ ] Prometheus dashboards (Grafana)
- [ ] Structured logging with correlation IDs
- [ ] Jaeger trace visualization
- [ ] Load test scenarios (Locust)
- [ ] Chaos testing (delayed WS, dropped events)
- [ ] SLO definitions and alerts
- [ ] Runbook documentation

**Success Criteria**:
- Traces cover all request paths
- Dashboards show key metrics (TTM, queue depth, etc.)
- Load tests handle 5000+ concurrent users
- Chaos tests identify failure modes
- Alerts fire correctly

---

## Future Phases (Post-MVP)

### Phase 9: Advanced Matchmaking
- Skill-based role assignment
- Dynamic MMR band tuning
- Multi-region fallback
- Party MMR weighting

### Phase 10: Social Features
- Friends list
- In-game chat persistence
- Player blocking
- Party voice channel allocation

### Phase 11: Anti-Cheat & Abuse Prevention
- Anomaly detection (queue manipulation)
- Behavioral analytics
- Automated ban system
- Report/appeal workflow

### Phase 12: Production Readiness
- Kubernetes deployment
- Multi-region replication
- Service mesh (Istio)
- Disaster recovery plan
- Auto-scaling policies

---

## Timeline (Estimated)

- **Phase 0**: Complete ✅
- **Phase 1**: Week 1
- **Phase 2**: Week 2
- **Phase 3**: Week 3
- **Phase 4**: Week 4-5
- **Phase 5**: Week 5-6
- **Phase 6**: Week 6-7
- **Phase 7**: Week 7-8
- **Phase 8**: Week 8-9

**Total**: ~8-9 weeks to MVP

---

## Success Metrics

**MVP Goals**:
- Support 10,000 concurrent players
- Average time-to-match < 30s
- p99 matchmaking latency < 100ms
- 99.9% uptime
- Match quality score > 0.85

---

## Next Steps

After Phase 0, proceed to **Phase 1: Database & Core Infrastructure**.

See the main README for quick start commands and the CONTRIBUTING guide for development workflow.
