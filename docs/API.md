# API Reference

Complete REST API reference for the Matchmaker Platform.

**Base URL**: `http://localhost:8080` (development)

**Authentication**: Most endpoints require JWT Bearer token authentication. Include in header:
```
Authorization: Bearer <access_token>
```

## Table of Contents

- [Authentication](#authentication)
- [Profile Management](#profile-management)
- [Party & Lobby](#party--lobby)
- [Session Management](#session-management)
- [Leaderboard & Match History](#leaderboard--match-history)
- [Error Responses](#error-responses)

---

## Authentication

### Register User

Create a new user account.

**Endpoint**: `POST /v1/auth/register`

**Authentication**: None required

**Request Body**:
```json
{
  "email": "player@example.com",
  "username": "player123",
  "password": "secure_password",
  "region": "us-west"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid-string",
  "username": "player123",
  "email": "player@example.com",
  "region": "us-west",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `400`: Invalid input (missing fields, weak password)
- `409`: Username or email already exists

---

### Login

Authenticate and receive JWT tokens.

**Endpoint**: `POST /v1/auth/login`

**Authentication**: None required

**Request Body**:
```json
{
  "username": "player123",
  "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Token Lifetimes**:
- Access Token: 15 minutes
- Refresh Token: 7 days

**Errors**:
- `400`: Missing credentials
- `401`: Invalid username or password

---

### Refresh Token

Obtain a new access token using refresh token.

**Endpoint**: `POST /v1/auth/refresh`

**Authentication**: None required (uses refresh token)

**Request Body**:
```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors**:
- `400`: Missing refresh token
- `401`: Invalid or expired refresh token

---

## Profile Management

### Get Current User Profile

Retrieve authenticated user's profile information.

**Endpoint**: `GET /v1/profile/me`

**Authentication**: Required (Bearer token)

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "username": "player123",
  "email": "player@example.com",
  "region": "us-west",
  "mmr": 1500,
  "rank": "Gold III",
  "wins": 42,
  "losses": 38,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `401`: Missing or invalid token

---

### Update Profile

Update user profile settings.

**Endpoint**: `PATCH /v1/profile/me`

**Authentication**: Required (Bearer token)

**Request Body** (all fields optional):
```json
{
  "region": "eu-west",
  "preferences": {
    "language": "en",
    "notifications": true
  }
}
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "username": "player123",
  "region": "eu-west",
  "preferences": {
    "language": "en",
    "notifications": true
  },
  "updated_at": "2025-01-15T11:00:00Z"
}
```

**Errors**:
- `400`: Invalid input
- `401`: Missing or invalid token

---

## Party & Lobby

### Create Party

Create a new party (lobby).

**Endpoint**: `POST /v1/party`

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "max_size": 5,
  "is_public": true
}
```

**Response** (201 Created):
```json
{
  "id": "party-uuid",
  "leader_id": "user-uuid",
  "members": [
    {
      "user_id": "user-uuid",
      "username": "player123",
      "is_ready": false,
      "joined_at": "2025-01-15T10:30:00Z"
    }
  ],
  "max_size": 5,
  "is_public": true,
  "is_in_queue": false,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `400`: Invalid max_size (must be 1-10)
- `401`: Missing or invalid token
- `409`: User already in a party

---

### Get Party Details

Retrieve party information.

**Endpoint**: `GET /v1/party/{party_id}`

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `party_id`: UUID of the party

**Response** (200 OK):
```json
{
  "id": "party-uuid",
  "leader_id": "user-uuid",
  "members": [...],
  "max_size": 5,
  "is_public": true,
  "is_in_queue": false,
  "queue_mode": null,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `401`: Missing or invalid token
- `404`: Party not found

---

### Join Party

Join an existing party.

**Endpoint**: `POST /v1/party/{party_id}/join`

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `party_id`: UUID of the party to join

**Response** (200 OK):
```json
{
  "id": "party-uuid",
  "members": [
    {
      "user_id": "original-user-uuid",
      "username": "player123",
      "is_ready": true
    },
    {
      "user_id": "new-user-uuid",
      "username": "player456",
      "is_ready": false
    }
  ],
  "max_size": 5
}
```

**Errors**:
- `400`: Party is full
- `401`: Missing or invalid token
- `404`: Party not found
- `409`: User already in a party

---

### Leave Party

Leave current party.

**Endpoint**: `DELETE /v1/party/{party_id}/leave`

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `party_id`: UUID of the party to leave

**Response** (204 No Content)

**Notes**:
- If leader leaves, party leadership transfers to next member
- If last member leaves, party is automatically deleted

**Errors**:
- `401`: Missing or invalid token
- `404`: Party not found or user not in party

---

### Toggle Ready Status

Toggle ready status in party.

**Endpoint**: `POST /v1/party/{party_id}/ready`

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `party_id`: UUID of the party

**Response** (200 OK):
```json
{
  "user_id": "user-uuid",
  "is_ready": true
}
```

**Errors**:
- `401`: Missing or invalid token
- `404`: Party not found or user not in party

---

### Enter Matchmaking Queue

Queue party for matchmaking.

**Endpoint**: `POST /v1/party/queue`

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "party_id": "party-uuid",
  "mode": "ranked",
  "team_size": 5
}
```

**Available Modes**:
- `ranked`: Competitive matchmaking with MMR
- `casual`: Unranked quick matches
- `custom`: Custom game modes

**Response** (200 OK):
```json
{
  "party_id": "party-uuid",
  "queue_mode": "ranked",
  "team_size": 5,
  "queued_at": "2025-01-15T10:35:00Z",
  "estimated_wait_seconds": 30
}
```

**Requirements**:
- All party members must be ready
- Party size must match team_size requirement
- Party must not already be in queue

**Errors**:
- `400`: Invalid mode or team size
- `401`: Missing or invalid token
- `404`: Party not found
- `409`: Party already in queue or not all members ready

---

### Leave Matchmaking Queue

Remove party from matchmaking queue.

**Endpoint**: `DELETE /v1/party/queue`

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `party_id`: UUID of the party

**Response** (204 No Content)

**Errors**:
- `401`: Missing or invalid token
- `404`: Party not found or not in queue

---

### WebSocket - Party Updates

Real-time party events and match notifications.

**Endpoint**: `WS /v1/ws/party/{party_id}`

**Authentication**: Required (token as query param)

**Connection**:
```
ws://localhost:8080/v1/ws/party/{party_id}?token=<access_token>
```

**Event Types**:

#### Member Joined
```json
{
  "event": "member_joined",
  "data": {
    "user_id": "user-uuid",
    "username": "player789"
  },
  "timestamp": "2025-01-15T10:36:00Z"
}
```

#### Member Left
```json
{
  "event": "member_left",
  "data": {
    "user_id": "user-uuid"
  },
  "timestamp": "2025-01-15T10:37:00Z"
}
```

#### Ready Status Changed
```json
{
  "event": "ready_changed",
  "data": {
    "user_id": "user-uuid",
    "is_ready": true
  },
  "timestamp": "2025-01-15T10:38:00Z"
}
```

#### Match Found
```json
{
  "event": "match_found",
  "data": {
    "match_id": "match-uuid",
    "server_endpoint": "game-server-1.example.com:7777",
    "server_token": "encrypted-token",
    "team_assignment": "blue",
    "teammates": ["user-1", "user-2"],
    "opponents": ["user-3", "user-4"]
  },
  "timestamp": "2025-01-15T10:39:00Z"
}
```

---

## Session Management

### Get Session Details

Retrieve game server connection details for a match.

**Endpoint**: `GET /v1/session/{match_id}`

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `match_id`: UUID of the match

**Response** (200 OK):
```json
{
  "match_id": "match-uuid",
  "server_endpoint": "game-server-1.example.com:7777",
  "server_token": "encrypted-token",
  "mode": "ranked",
  "map": "desert_storm",
  "team_size": 5,
  "expires_at": "2025-01-15T11:39:00Z"
}
```

**Errors**:
- `401`: Missing or invalid token
- `404`: Match not found
- `403`: User not part of this match

---

### Game Server Heartbeat

Game servers send periodic heartbeats to maintain session.

**Endpoint**: `POST /v1/session/{match_id}/heartbeat`

**Authentication**: Required (Server token)

**Path Parameters**:
- `match_id`: UUID of the match

**Request Body**:
```json
{
  "player_count": 10,
  "status": "in_progress"
}
```

**Response** (200 OK):
```json
{
  "acknowledged": true,
  "next_heartbeat_seconds": 30
}
```

**Errors**:
- `401`: Invalid server token
- `404`: Match not found

---

### Submit Match Result

Game server submits final match results.

**Endpoint**: `POST /v1/session/{match_id}/result`

**Authentication**: Required (Server token)

**Path Parameters**:
- `match_id`: UUID of the match

**Request Body**:
```json
{
  "winning_team": "blue",
  "duration_seconds": 1823,
  "player_stats": [
    {
      "user_id": "user-uuid",
      "kills": 12,
      "deaths": 5,
      "assists": 8,
      "score": 3200
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "match_id": "match-uuid",
  "processed": true,
  "mmr_changes": {
    "user-uuid": +25
  }
}
```

**Errors**:
- `400`: Invalid result data
- `401`: Invalid server token
- `404`: Match not found

---

## Leaderboard & Match History

### Get Match History

Retrieve paginated match history.

**Endpoint**: `GET /v1/matches/history`

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `player_id` (optional): Filter by player UUID
- `mode` (optional): Filter by game mode
- `limit` (optional): Results per page (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Example Request**:
```
GET /v1/matches/history?player_id=user-uuid&mode=ranked&limit=10
```

**Response** (200 OK):
```json
{
  "matches": [
    {
      "match_id": "match-uuid",
      "mode": "ranked",
      "start_time": "2025-01-15T10:39:00Z",
      "end_time": "2025-01-15T11:09:00Z",
      "duration_seconds": 1800,
      "result": "victory",
      "mmr_change": +25,
      "player_stats": {
        "kills": 15,
        "deaths": 7,
        "assists": 12
      }
    }
  ],
  "total": 142,
  "limit": 10,
  "offset": 0
}
```

**Errors**:
- `400`: Invalid query parameters
- `401`: Missing or invalid token

---

### Get Leaderboard

Retrieve seasonal leaderboard rankings.

**Endpoint**: `GET /v1/leaderboard`
**Endpoint**: `GET /v1/leaderboard/{season}`

**Authentication**: Optional (public endpoint, but auth shows your rank)

**Path Parameters**:
- `season` (optional): Season identifier (defaults to current season)

**Query Parameters**:
- `region` (optional): Filter by region
- `limit` (optional): Results per page (default: 100, max: 1000)
- `offset` (optional): Pagination offset

**Example Request**:
```
GET /v1/leaderboard?region=us-west&limit=50
```

**Response** (200 OK):
```json
{
  "season": "2025-S1",
  "region": "us-west",
  "updated_at": "2025-01-15T12:00:00Z",
  "rankings": [
    {
      "rank": 1,
      "user_id": "user-uuid",
      "username": "ProPlayer",
      "mmr": 3450,
      "wins": 245,
      "losses": 123,
      "win_rate": 0.666
    },
    {
      "rank": 2,
      "user_id": "user-uuid-2",
      "username": "TopGamer",
      "mmr": 3380,
      "wins": 198,
      "losses": 102,
      "win_rate": 0.660
    }
  ],
  "total": 15234,
  "limit": 50,
  "offset": 0,
  "your_rank": 142
}
```

**Errors**:
- `404`: Season not found

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "details": {
      "field": "Additional context"
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Request successful, no response body
- `400 Bad Request`: Invalid input or request format
- `401 Unauthorized`: Missing, invalid, or expired authentication
- `403 Forbidden`: Authenticated but not authorized for this resource
- `404 Not Found`: Resource does not exist
- `409 Conflict`: Request conflicts with current state (e.g., already in party)
- `422 Unprocessable Entity`: Valid format but semantic errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Service temporarily unavailable

### Rate Limits

API endpoints are rate-limited per user:
- **Authentication endpoints**: 5 requests per minute
- **Read endpoints**: 100 requests per minute
- **Write endpoints**: 30 requests per minute
- **WebSocket connections**: 5 concurrent connections per user

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642257600
```

---

## Interactive Documentation

For interactive API exploration with request examples:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
