# Lobby/Party Service

Python service managing party creation, invites, and ready checks.

## Responsibilities

- Create/join/leave parties
- Party invitations and kick operations
- Ready check coordination
- Translation of party state to matchmaking queue events

## Implementation Status

- [ ] Phase 3: Party CRUD operations
- [ ] Phase 3: Ready check logic
- [ ] Phase 3: Integration with matchmaker

## Running

```bash
# Development
python main.py

# With Docker
docker compose up lobby
```
