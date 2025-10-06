# Session Service

Manages game session allocation and lifecycle.

## Responsibilities

- Allocate game server endpoints (mock or real)
- Session lifecycle (allocating → active → ended)
- Heartbeat tracking and timeout detection
- Match result writeback to database

## Implementation Status

- [ ] Phase 5: Session allocation (mock)
- [ ] Phase 5: Lifecycle management
- [ ] Phase 5: Heartbeat tracking
- [ ] Integration with dedicated servers

## Running

```bash
# Development
python main.py

# With Docker
docker compose up session
```
