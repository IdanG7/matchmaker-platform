# Gateway API Service

FastAPI-based gateway providing REST and WebSocket endpoints.

## Responsibilities

- REST endpoints for auth, profiles, queues, lobbies, sessions
- WebSocket connections for real-time events
- JWT validation and rate limiting
- Request routing to backend services via NATS

## Implementation Status

- [ ] Phase 2: Auth endpoints
- [ ] Phase 2: Profile endpoints
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
