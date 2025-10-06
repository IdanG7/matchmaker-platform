# Gateway API Service

FastAPI-based gateway providing REST and WebSocket endpoints.

## Responsibilities

- REST endpoints for auth, profiles, queues, lobbies, sessions
- WebSocket connections for real-time events
- JWT validation and rate limiting
- Request routing to backend services via NATS

## Implementation Status

- [x] Phase 2: Auth endpoints (register, login, refresh)
- [x] Phase 2: Profile endpoints (get, update)
- [x] Phase 2: JWT authentication and validation
- [x] Phase 2: Redis-based rate limiting
- [ ] Phase 3: Party/lobby endpoints
- [ ] Phase 4: Matchmaking endpoints
- [ ] Phase 5: Session endpoints
- [ ] WebSocket event handling

## Running

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# With Docker
docker compose up api
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
