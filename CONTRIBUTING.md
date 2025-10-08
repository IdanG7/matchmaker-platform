# Contributing Guide

## Development Setup

### Prerequisites

- Python 3.12+
- CMake 3.20+
- Docker & Docker Compose
- C++20 compatible compiler (GCC 11+, Clang 14+, or MSVC 2022+)

### Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd multiplayer

# Copy environment file
cp .env.example .env

# Start infrastructure
make up

# Run tests
make test
```

## Project Structure

```
services/       # Microservices (Python FastAPI + C++)
sdk/           # Client SDKs
deployments/   # Docker Compose & Kubernetes configs
db/            # Database migrations
ops/           # Observability configs
tests/         # Integration & load tests
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the coding standards for each language:

**Python**

- Use Black for formatting
- Follow PEP 8
- Type hints required
- Docstrings for public APIs

**C++**

- Use clang-format (LLVM style)
- C++20 standard
- RAII patterns
- Smart pointers over raw pointers

### 3. Write Tests

- Unit tests required for all new code
- Integration tests for service interactions
- Minimum 80% coverage for Python services

### 4. Run Tests Locally

```bash
# All tests
make test

# Python only
pytest tests/unit -v

# C++ only
cd services/matchmaker && cmake -B build && ctest --test-dir build
```

### 5. Commit Changes

We use **[Conventional Commits](https://www.conventionalcommits.org/)** for automated versioning and changelog generation.

#### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Examples:**

```bash
# Feature - triggers MINOR version bump (0.1.0 -> 0.2.0)
git commit -m "feat: add WebSocket reconnection logic"
git commit -m "feat(sdk): add party invite functionality"

# Fix - triggers PATCH version bump (0.1.0 -> 0.1.1)
git commit -m "fix: resolve memory leak in matchmaker"
git commit -m "fix(api): handle null player stats gracefully"

# Breaking change - triggers MAJOR version bump (0.1.0 -> 1.0.0)
git commit -m "feat!: redesign authentication API"
# OR with footer:
git commit -m "feat: redesign authentication API

BREAKING CHANGE: Auth endpoints now require OAuth2 instead of JWT"
```

#### Commit Types

- **feat**: New feature → MINOR version bump
- **fix**: Bug fix → PATCH version bump
- **docs**: Documentation only (no version bump)
- **style**: Code style/formatting (no version bump)
- **refactor**: Code refactoring (no version bump)
- **perf**: Performance improvement → PATCH version bump
- **test**: Adding/updating tests (no version bump)
- **build**: Build system changes (no version bump)
- **ci**: CI/CD changes (no version bump)
- **chore**: Maintenance tasks (no version bump)

#### Breaking Changes

Mark breaking changes with `!` or `BREAKING CHANGE:` footer:

```bash
# Using !
git commit -m "feat!: remove deprecated matchmaker v1 API"

# Using footer (more descriptive)
git commit -m "refactor: change party data structure

BREAKING CHANGE: Party.members is now an array of objects instead of strings.
Migration guide in docs/migration.md"
```

#### Scopes (Optional)

Scopes help organize changes by component:

- `api` - API service
- `matchmaker` - Matchmaker service
- `sdk` - Client SDK
- `db` - Database changes
- `ci` - CI/CD workflows

**Example:** `feat(sdk): add reconnection backoff strategy`

#### How Releases Work

1. **You commit** using conventional commit format
2. **Release Please** creates/updates a release PR with:
   - Version bump based on commits
   - Auto-generated changelog
3. **When you merge the PR**, a new release is:
   - Tagged automatically
   - Published to GitHub Releases
   - SDK binaries built and attached

**Note:** Only commits to `main` trigger releases. Feature branches don't create releases.

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:

- Clear description of changes
- Related issue numbers
- Screenshots/logs if applicable

## Service Development

### Adding a New Python Service

1. Create service directory in `services/`
2. Add `main.py` with FastAPI app
3. Add `requirements.txt`
4. Create Dockerfile
5. Add to docker-compose.yml
6. Add tests in `tests/unit/`

### Adding a New C++ Component

1. Create directories in appropriate location
2. Add CMakeLists.txt
3. Implement headers in `include/`
4. Implement sources in `src/`
5. Add tests in `tests/`

## Testing

### Unit Tests

```bash
# Python
pytest tests/unit -v --cov

# C++
cd <service> && cmake -B build && ctest --test-dir build
```

### Integration Tests

```bash
make up
pytest tests/integration -v
```

### Load Tests

```bash
cd tests/load
locust -f locustfile.py
```

## Code Review

All PRs require:

- Passing CI checks
- Code review approval
- No merge conflicts
- Updated documentation if needed

## Database Migrations

```sql
-- Create migration file in db/migrations/
-- Name format: YYYYMMDD_description.sql

-- Example: 20250106_add_player_stats.sql
ALTER TABLE game.player ADD COLUMN stats JSONB DEFAULT '{}'::jsonb;
```

## Observability

### Adding Metrics

```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
```

### Adding Traces

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("operation_name"):
    # Your code here
    pass
```

## Getting Help

- GitHub Issues: Bug reports and feature requests
- Discussions: Questions and general discussion
- Documentation: See `/docs` directory

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
