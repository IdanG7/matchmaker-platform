# Production CI/CD Setup Guide

This document outlines the professional CI/CD setup for the multiplayer matchmaking platform.

## Architecture Overview

```
┌─────────────┐
│   PR Created│
└──────┬──────┘
       │
       ├─────► Commit Message Validation
       ├─────► Python Linting (Black, Flake8, Bandit)
       ├─────► Python Unit Tests
       ├─────► C++ Builds (Matchmaker + SDK)
       ├─────► Integration Tests
       ├─────► SDK E2E Tests
       ├─────► Security Scanning
       │
       ▼
┌──────────────┐
│ All Tests ✅ │──► PR can be merged
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Merge to main│
└──────┬───────┘
       │
       ├─────► Release-Please analyzes commits
       │       └─► Creates release PR (if needed)
       │
       ▼
┌──────────────┐
│ Release PR   │──► Contains:
│ Created      │    - Version bump
└──────┬───────┘    - Auto-generated CHANGELOG
       │            - Updated version files
       │
       ▼
┌──────────────┐
│ Review & Merge Release PR │
└──────┬───────┘
       │
       ├─────► CI tests run again
       │
       ▼
┌──────────────┐
│ Release      │
│ Published    │
└──────┬───────┘
       │
       ├─────► Wait for CI to pass ✅
       ├─────► Build SDK (Linux + macOS)
       ├─────► Package SDK binaries
       └─────► Upload to GitHub Release
```

## Workflow Files

### 1. `ci.yml` - Main CI Pipeline

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

**Jobs:**
- `validate-commits` - Validates conventional commit format (PR only)
- `lint-python` - Black, Flake8, Bandit security scanning
- `test-python` - Unit tests with PostgreSQL/Redis/NATS
- `build-matchmaker` - C++ matchmaker compilation and tests
- `build-sdk` - C++ SDK compilation and tests
- `integration-test` - Full stack integration tests
- `sdk-integration-test` - End-to-end SDK tests
- `security-scan` - Trivy vulnerability scanning
- `docker-build` - Build and push Docker images (main only)
- `summary` - Aggregate all test results

**Critical:** All jobs must pass before merge is allowed.

### 2. `release-please.yml` - Release Automation

**Triggers:**
- Push to `main`

**Job:**
- `release-please` - Analyzes conventional commits and:
  - Creates/updates release PR with changelog
  - When release PR is merged → publishes GitHub release

**Does NOT build SDK** - that's handled by `release.yml`

### 3. `release.yml` - SDK Release Build

**Triggers:**
- GitHub release published

**Jobs:**
- `wait-for-ci` - Waits for CI pipeline to pass
- `build-sdk` - Builds SDK for Linux and macOS (only if CI passed)
- `upload-assets` - Uploads binaries to GitHub Release

**Critical:** This ensures SDKs are only released if all tests pass.

## Required Status Checks Setup

To enforce test passing before merge, configure branch protection:

### Steps:

1. Go to: `https://github.com/YOUR_USERNAME/multiplayer/settings/branches`

2. Click **"Add branch protection rule"**

3. Branch name pattern: `main`

4. Enable:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging**
     - **Require branches to be up to date before merging**
   - **Require conversation resolution before merging**

5. Search and select required status checks:
   ```
   - Python Linting
   - Python Unit Tests
   - Build & Test C++ Matchmaker
   - Build & Test C++ SDK
   - Integration Tests (Full Stack)
   - SDK End-to-End Test
   - Security Scanning
   ```

6. Additional settings (recommended):
   - **Require linear history**
   - **Do not allow bypassing the above settings**

7. Click **"Create"** or **"Save changes"**

### Result:

After setup:
- Cannot merge PR if any test fails
- Cannot merge PR if branch is behind main
- Only passing, tested code reaches main
- Releases only contain verified code

## Conventional Commits Enforcement

Commit messages are validated on PRs using commitlint:

**Valid:**
```bash
feat: add WebSocket reconnection
fix(api): handle null player stats
docs: update README
```

**Invalid:**
```bash
Added feature          # Missing type
fix added bug         # Wrong format
WIP                   # Not descriptive
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full conventional commits guide.

## Release Process

### Automatic (Recommended):

1. **Develop normally** with conventional commits:
   ```bash
   git commit -m "feat(sdk): add party invite system"
   git commit -m "fix(matchmaker): resolve memory leak"
   ```

2. **Push to main** (via PR merge):
   - All tests must pass ✅
   - PR gets merged

3. **Release-please creates release PR**:
   - Analyzes commits since last release
   - Determines version bump (0.1.1 → 0.2.0 for feat)
   - Generates CHANGELOG

4. **Review and merge release PR**:
   - Check changelog accuracy
   - Verify version bump is correct
   - Merge when ready

5. **Automatic SDK build**:
   - Waits for CI to pass
   - Builds Linux + macOS binaries
   - Uploads to GitHub Release

### Manual (Emergency):

If you need to create a release manually:

```bash
# Create and push tag
git tag v0.1.2
git push origin v0.1.2

# Manually create GitHub release at:
# https://github.com/YOUR_USERNAME/multiplayer/releases/new

# SDK build will trigger automatically
```

## Monitoring Releases

### Check Release Status:

1. **Release PR status**: https://github.com/YOUR_USERNAME/multiplayer/pulls
2. **Workflow runs**: https://github.com/YOUR_USERNAME/multiplayer/actions
3. **Published releases**: https://github.com/YOUR_USERNAME/multiplayer/releases

### Troubleshooting:

**Problem:** Release PR not created after merge
- **Check:** Did commits follow conventional format?
- **Check:** Was there already a release PR open?
- **Fix:** Verify commits with `git log --oneline`

**Problem:** SDK binaries not building
- **Check:** Did CI pass before release?
- **Check:** Release workflow logs
- **Fix:** Re-run workflow or create manual release

**Problem:** CI failing on main
- **Check:** Which job failed in Actions tab
- **Fix:** Hotfix PR with `fix:` commit
- **Note:** No release will be created until CI passes

## Best Practices

### For Contributors:

1. **Always use conventional commits**
2. **Write tests for new features**
3. **Ensure CI passes locally before pushing**
4. **Keep PRs focused and small**
5. **Update docs with code changes**

### For Maintainers:

1. **Review release PRs carefully**
2. **Test releases before announcing**
3. **Monitor CI pipeline health**
4. **Keep dependencies updated**
5. **Respond to security scan alerts**

## Security Considerations

### Automated Scanning:

- **Bandit**: Python security issues (runs on every PR)
- **Trivy**: Container vulnerability scanning
- **Dependabot**: Dependency updates (configure in repo settings)

### Manual Reviews:

- Review security scan results in Actions artifacts
- Check Dependabot PRs regularly
- Monitor GitHub Security tab

## Performance Optimization

### CI Speed:

- **Parallel jobs**: Tests run concurrently
- **Caching**: pip, CMake builds cached
- **Selective runs**: Only affected services tested

### Release Speed:

- **Matrix builds**: Linux + macOS build in parallel
- **Artifact caching**: Speeds up multi-job workflows

## Next Steps: Phase 8

Phase 8 (Observability & Production Readiness) includes:

1. **Prometheus + Grafana** - Metrics and dashboards
2. **Jaeger** - Distributed tracing
3. **ELK Stack** - Centralized logging
4. **Alerting** - PagerDuty/Slack integration
5. **Load Testing** - Locust-based performance tests
6. **Chaos Engineering** - Resilience testing

See [PHASE-8-PLAN.md](./PHASE-8-PLAN.md) for detailed implementation plan.

---

**Questions?** Open an issue or discussion on GitHub.
