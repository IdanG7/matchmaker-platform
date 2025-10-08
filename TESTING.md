# Testing Guide

This document describes the testing strategy and how to run tests for the Multiplayer Matchmaking Platform.

## Test Coverage

The project has comprehensive test coverage across multiple layers:

- **Python Unit Tests**: 50+ tests for API services
- **C++ Unit Tests**: 12+ tests for SDK, 11+ tests for Matchmaker
- **Integration Tests**: End-to-end API flow testing
- **SDK Integration Tests**: Real client-server communication
- **Security Scans**: Bandit (Python) and Trivy (dependencies)

## Running Tests Locally

### Python Tests

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all Python tests
cd services/api
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html
```

### C++ Matchmaker Tests

```bash
cd services/matchmaker
cmake -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

### C++ SDK Tests

```bash
cd sdk/cpp
cmake -B build -DBUILD_TESTS=ON
cmake --build build
./build/sdk_tests
```

### SDK End-to-End Test

This test requires the backend services to be running:

```bash
# Terminal 1: Start services
make up

# Terminal 2: Run SDK test
cd sdk/cpp/build
./examples/party_test
```

Expected output:
```
=== SDK Party Test ===
1. Registering Player 1...
   ✓ Player 1 authenticated
2. Registering Player 2...
   ✓ Player 2 authenticated
3. Player 1 creating party...
   ✓ Party created: <party-id>
4. Player 1 connecting to party WebSocket...
   ✓ WebSocket connected
5. Player 2 joining party <party-id>...
   📡 Received lobby update!
   ✓ Player 2 joined party
6. Waiting for WebSocket events...
   ✓ Received member_joined event via WebSocket
7. Disconnecting WebSocket...
   ✓ Disconnected
```

### Integration Tests

```bash
# Start services first
make up

# Run integration tests
pip install httpx pytest-asyncio
pytest tests/integration/ -v
```

## CI/CD Testing

The GitHub Actions CI pipeline runs automatically on all PRs and commits to `main`:

### Pipeline Stages

1. **Python Linting**
   - Black formatter check
   - Flake8 linter
   - Bandit security scanner

2. **Python Unit Tests**
   - Runs with PostgreSQL, Redis, and NATS services
   - Generates code coverage report
   - Uploads to Codecov

3. **C++ Matchmaker Build & Test**
   - CMake configuration and build
   - CTest execution
   - Test artifact upload

4. **C++ SDK Build & Test**
   - CMake configuration and build
   - Unit test execution
   - Binary artifact upload

5. **Integration Tests**
   - Full Docker Compose stack
   - API endpoint validation
   - Service health checks

6. **SDK Integration Test**
   - Full stack with backend services
   - SDK party_test execution
   - Real WebSocket communication

7. **Security Scanning**
   - Trivy vulnerability scanner
   - SARIF report upload to GitHub Security

8. **Docker Build**
   - Multi-stage image builds
   - Container registry push (main branch only)

## Test Organization

```
tests/
├── integration/          # Integration tests (Python)
│   ├── __init__.py
│   └── test_api_endpoints.py
services/
├── api/
│   └── tests/           # Python unit tests
│       ├── test_auth_utils.py
│       ├── test_party.py
│       └── ...
├── matchmaker/
│   └── tests/           # C++ matchmaker tests
│       └── test_matchmaker.cpp
sdk/
└── cpp/
    └── tests/           # C++ SDK tests
        └── test_main.cpp
```

## Coverage Goals

- **Overall Coverage**: 85%+
- **Critical Paths**: 95%+
  - Authentication
  - Party management
  - Matchmaking logic
  - WebSocket events

## Test Best Practices

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test service interactions
3. **E2E Tests**: Test complete user flows
4. **Mock External Dependencies**: Use mocks for third-party services
5. **Clean State**: Reset database/cache between tests
6. **Descriptive Names**: Use clear, descriptive test names
7. **Fast Execution**: Keep unit tests under 1 second each

## Debugging Failed Tests

### Local Debugging

```bash
# Run a specific test with verbose output
pytest tests/test_party.py::test_create_party -vv

# Run with debugging breakpoint
pytest tests/test_party.py --pdb

# Show print statements
pytest tests/test_party.py -s
```

### CI Debugging

1. Check the GitHub Actions logs
2. Download test artifacts (coverage reports, logs)
3. Reproduce locally using the same environment:
   ```bash
   docker compose -f deployments/docker/docker-compose.yml up -d
   pytest tests/integration/ -v
   ```

## Performance Testing

For load testing (Phase 8):

```bash
# Coming soon: Locust load tests
locust -f tests/load/locustfile.py --host=http://localhost:8080
```

## Security Testing

```bash
# Python security scan
bandit -r services/api -ll

# Dependency vulnerability scan
trivy fs .
```

## Continuous Improvement

- Add tests for all new features
- Maintain >85% coverage
- Update integration tests for new endpoints
- Add performance benchmarks
- Document test scenarios
