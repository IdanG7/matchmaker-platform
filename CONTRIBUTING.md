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

```bash
git add .
git commit -m "feat: add new feature"
```

Commit message format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

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
