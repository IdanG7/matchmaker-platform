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

## Phase 2: Auth & Profile Service

**Duration**: ~5-7 days

**Goals**:
- JWT-based authentication
- User registration and login
- Profile management
- Rate limiting

**Tasks**:
- [ ] Implement password hashing (bcrypt)
- [ ] JWT token generation and validation
- [ ] `POST /v1/auth/register` endpoint
- [ ] `POST /v1/auth/login` endpoint
- [ ] `POST /v1/auth/refresh` endpoint
- [ ] `GET /v1/profile/me` endpoint
- [ ] `PATCH /v1/profile/me` endpoint
- [ ] Redis-based rate limiting
- [ ] Profile service NATS handlers
- [ ] Unit tests for auth flows

**Success Criteria**:
- Users can register and login
- JWT tokens issued and validated
- Profile CRUD operations work
- Rate limiting prevents abuse
- 90%+ test coverage

---

## Phase 3: Lobby/Party Service

**Duration**: ~5-7 days

**Goals**:
- Party creation and management
- Ready check system
- Integration with matchmaking queue

**Tasks**:
- [ ] `POST /v1/party` - Create party
- [ ] `POST /v1/party/{id}/join` - Join party
- [ ] `POST /v1/party/{id}/leave` - Leave party
- [ ] `POST /v1/party/{id}/invite` - Invite player
- [ ] `POST /v1/party/{id}/ready` - Ready check
- [ ] WebSocket lobby events
- [ ] Redis party state management
- [ ] NATS integration for queue events
- [ ] Unit and integration tests

**Success Criteria**:
- Players can create/join/leave parties
- Ready check works correctly
- Party state synced via WebSocket
- Queue events published to matchmaker

---

## Phase 4: Matchmaker Core (C++)

**Duration**: ~7-10 days

**Goals**:
- High-performance tick-based matchmaking
- Region/MMR/latency constraints
- Team formation algorithm
- Backfill support

**Tasks**:
- [ ] Redis client integration (hiredis)
- [ ] NATS client integration
- [ ] Queue bucket management (region/mode)
- [ ] MMR band calculation with time-based widening
- [ ] Team formation algorithm
- [ ] Match quality scoring
- [ ] Backfill queue handling
- [ ] Prometheus metrics export
- [ ] Unit tests with mocked Redis/NATS
- [ ] Load testing (1000+ concurrent queues)

**Success Criteria**:
- Matchmaker tick < 10ms p99
- Correct team formation (balanced MMR)
- Backfill slots handled
- Graceful degradation under load
- Metrics exported to Prometheus

---

## Phase 5: Session Service

**Duration**: ~4-6 days

**Goals**:
- Game session allocation
- Lifecycle management
- Server endpoint distribution

**Tasks**:
- [ ] Mock server allocator (returns static endpoint)
- [ ] Session lifecycle FSM (allocating → active → ended)
- [ ] `GET /v1/session/{match_id}` endpoint
- [ ] Session token generation (HMAC)
- [ ] Heartbeat tracking with Redis TTL
- [ ] Match result writeback to database
- [ ] NATS event consumers
- [ ] Unit tests for lifecycle

**Success Criteria**:
- Sessions allocated when match found
- Players receive server endpoint + token
- Heartbeats tracked correctly
- Match results persisted
- Timeouts handled gracefully

---

## Phase 6: Leaderboard & Match History

**Duration**: ~4-6 days

**Goals**:
- Persistent match history
- Seasonal leaderboards
- Efficient top-N queries

**Tasks**:
- [ ] Match history table schema
- [ ] `GET /v1/matches/history` endpoint (paginated)
- [ ] `GET /v1/leaderboard/{season}` endpoint
- [ ] MMR calculation (Elo/Glicko stub)
- [ ] Async leaderboard recalc via NATS
- [ ] Seasonal ranking materialized views
- [ ] Index optimization for queries
- [ ] Unit tests for ranking logic

**Success Criteria**:
- Match history queryable by player
- Leaderboard queries < 100ms p95
- Seasonal rankings update correctly
- MMR changes reflected

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
