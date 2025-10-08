# Phase 8: Production Observability & Reliability

**Status:** 🟡 In Progress
**Goal:** Transform from "works" to "production-ready enterprise platform"

## Current State vs. Target

| Aspect | Current | Target |
|--------|---------|--------|
| Monitoring | ❌ None | ✅ Full metrics, dashboards |
| Tracing | ❌ None | ✅ Distributed tracing |
| Logging | ❌ Scattered stdout | ✅ Centralized, searchable |
| Alerting | ❌ None | ✅ PagerDuty/Slack |
| Load Testing | ❌ None | ✅ Automated, continuous |
| Error Tracking | ❌ Logs only | ✅ Sentry integration |
| Performance | ❌ Unknown | ✅ P50/P95/P99 tracked |
| SLOs/SLIs | ❌ None | ✅ Defined & monitored |

## Implementation Plan

### 1. Metrics & Monitoring (Prometheus + Grafana)

**Goal:** Real-time visibility into system health and performance.

#### 1.1 Prometheus Setup

**Files to create:**
```
deployments/docker/prometheus/
├── prometheus.yml          # Scrape configs
├── alerts.yml             # Alert rules
└── Dockerfile

ops/prometheus/
├── rules/
│   ├── api.rules.yml
│   ├── matchmaker.rules.yml
│   └── system.rules.yml
└── alerts/
    ├── api.alerts.yml
    └── matchmaker.alerts.yml
```

**Metrics to track:**
- **API Service:**
  - Request rate (requests/sec)
  - Response time (P50, P95, P99)
  - Error rate (4xx, 5xx)
  - Active WebSocket connections
  - JWT validation latency

- **Matchmaker:**
  - Queue size per mode/region
  - Match creation rate
  - Average time-to-match
  - Match quality score
  - Active lobbies

- **Database:**
  - Query latency
  - Connection pool usage
  - Slow query count

- **Redis:**
  - Cache hit/miss rate
  - Queue depth
  - Memory usage

- **System:**
  - CPU usage per service
  - Memory usage
  - Network I/O
  - Disk I/O

**Implementation steps:**
```bash
# 1. Add Prometheus client to Python services
pip install prometheus-client

# 2. Add metrics middleware to FastAPI
# 3. Expose /metrics endpoint
# 4. Configure Prometheus scraping
# 5. Add service discovery
```

#### 1.2 Grafana Dashboards

**Dashboards to create:**
1. **Overview Dashboard**
   - System health at-a-glance
   - Active users
   - Request throughput
   - Error rates

2. **API Service Dashboard**
   - Endpoint latencies
   - Status code breakdown
   - Top slowest endpoints
   - WebSocket connections

3. **Matchmaker Dashboard**
   - Queue metrics per mode
   - Match creation funnel
   - Time-to-match distribution
   - Quality score trends

4. **Infrastructure Dashboard**
   - CPU/Memory per service
   - Database performance
   - Redis performance
   - Network metrics

5. **Business Metrics Dashboard**
   - Daily active users
   - Matches per hour
   - Peak concurrent players
   - Retention metrics

**Files:**
```
ops/grafana/
├── dashboards/
│   ├── overview.json
│   ├── api.json
│   ├── matchmaker.json
│   ├── infrastructure.json
│   └── business.json
└── provisioning/
    ├── datasources.yml
    └── dashboards.yml
```

### 2. Distributed Tracing (Jaeger)

**Goal:** Trace requests across microservices to identify bottlenecks.

**Setup:**
```
deployments/docker/jaeger/
├── docker-compose.jaeger.yml
└── config.yml

services/api/tracing.py
services/matchmaker/src/tracing.hpp
```

**What to trace:**
- API request → Database query → Redis cache → NATS message
- Matchmaking flow: Queue join → Match found → Lobby created
- Authentication flow: Login → JWT generation → Profile fetch

**Implementation:**
```python
# services/api/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

def setup_tracing(service_name: str):
    provider = TracerProvider()
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(provider)
```

**Spans to create:**
- `http.request` - Full HTTP request
- `db.query` - Database queries
- `cache.get` / `cache.set` - Redis operations
- `nats.publish` / `nats.subscribe` - Message bus
- `matchmaker.find_match` - Matchmaking logic

### 3. Centralized Logging (ELK Stack)

**Goal:** All logs in one place, searchable and analyzable.

**Stack:**
- **Elasticsearch** - Log storage and search
- **Logstash** - Log aggregation and parsing
- **Kibana** - Log visualization and dashboards
- **Filebeat** - Log shipping from containers

**Files:**
```
deployments/docker/elk/
├── elasticsearch.yml
├── logstash.conf
├── kibana.yml
└── filebeat.yml

ops/elk/
├── pipelines/
│   ├── api-logs.conf
│   └── matchmaker-logs.conf
└── dashboards/
    ├── api-errors.json
    └── matchmaker-performance.json
```

**Log structure (JSON):**
```json
{
  "timestamp": "2025-10-08T12:34:56.789Z",
  "service": "api",
  "level": "error",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "user_id": "uuid",
  "endpoint": "/v1/party/queue",
  "message": "Failed to join queue",
  "error": {
    "type": "QueueFullError",
    "message": "Queue capacity exceeded",
    "stack": "..."
  },
  "context": {
    "party_id": "uuid",
    "mode": "ranked",
    "team_size": 5
  }
}
```

**Log levels:**
- `DEBUG` - Development only
- `INFO` - Normal operations (request logs)
- `WARN` - Recoverable issues (retries, degradation)
- `ERROR` - Errors requiring attention
- `CRITICAL` - System-breaking issues

### 4. Alerting & Incident Response

**Goal:** Get notified before users complain.

#### Alert Rules

**Critical (PagerDuty):**
```yaml
# API is down
- alert: APIDown
  expr: up{job="api"} == 0
  for: 1m

# High error rate
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m

# Matchmaker not processing
- alert: MatchmakerStalled
  expr: rate(matches_created_total[5m]) == 0 AND queue_size > 10
  for: 10m
```

**Warning (Slack):**
```yaml
# Elevated latency
- alert: HighLatency
  expr: histogram_quantile(0.95, http_request_duration_seconds) > 1.0
  for: 10m

# Database slow queries
- alert: SlowQueries
  expr: rate(pg_slow_queries_total[5m]) > 10
  for: 5m
```

#### Runbooks

Create runbooks for common alerts:
```
ops/runbooks/
├── api-down.md
├── high-error-rate.md
├── matchmaker-stalled.md
├── database-slow.md
└── out-of-memory.md
```

### 5. Load & Performance Testing

**Goal:** Know your limits before production.

#### Load Testing with Locust

**Files:**
```
tests/load/
├── locustfile.py
├── scenarios/
│   ├── auth_flow.py
│   ├── matchmaking_flow.py
│   ├── party_management.py
│   └── websocket_stress.py
└── reports/
    └── .gitkeep
```

**Test scenarios:**
```python
# tests/load/scenarios/matchmaking_flow.py
from locust import HttpUser, task, between

class MatchmakingUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        response = self.client.post("/v1/auth/login", json={
            "username": f"loadtest_{self.context.get('user_id')}",
            "password": "test123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def create_and_join_queue(self):
        # Create party
        party = self.client.post("/v1/party", headers=self.headers).json()

        # Join queue
        self.client.post(
            f"/v1/party/queue",
            headers=self.headers,
            json={"party_id": party["id"], "mode": "ranked", "team_size": 5}
        )

        # Wait for match (poll)
        # ...
```

**Load test targets:**
- **Baseline:** 100 concurrent users
- **Target:** 1,000 concurrent users
- **Stretch:** 10,000 concurrent users

**Metrics to measure:**
- Throughput (requests/sec)
- Response times (P50, P95, P99)
- Error rate
- Resource usage (CPU, memory)
- Time-to-match under load

#### Continuous Performance Testing

Add to CI/CD:
```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - name: Start backend
        run: docker compose up -d

      - name: Run load test
        run: |
          locust -f tests/load/locustfile.py \
            --headless \
            --users 1000 \
            --spawn-rate 50 \
            --run-time 10m \
            --host http://localhost:8080

      - name: Generate report
        run: # ... generate HTML report

      - name: Upload results
        # ... upload to S3 or artifact storage
```

### 6. Error Tracking (Sentry)

**Goal:** Catch errors in production with context.

```python
# services/api/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% of transactions
    environment=os.getenv("ENV", "production"),
    release=os.getenv("GIT_SHA"),
)
```

**Sentry features:**
- Automatic error grouping
- Stack traces with source code
- User context (who hit the error)
- Breadcrumbs (what led to error)
- Performance monitoring

### 7. SLOs & SLIs

**Goal:** Define and track service reliability targets.

#### Service Level Indicators (SLIs)

```yaml
# ops/slos/api-slis.yml
slis:
  - name: api_availability
    description: "% of requests that succeed"
    query: |
      sum(rate(http_requests_total{status!~"5.."}[30d]))
      /
      sum(rate(http_requests_total[30d]))

  - name: api_latency
    description: "% of requests under 500ms"
    query: |
      histogram_quantile(0.95, http_request_duration_seconds_bucket) < 0.5
```

#### Service Level Objectives (SLOs)

```yaml
# ops/slos/api-slos.yml
slos:
  - name: API Availability
    sli: api_availability
    target: 99.9%  # Three nines
    window: 30d

  - name: API Latency
    sli: api_latency
    target: 95%    # P95 under 500ms
    window: 7d
```

#### Error Budget

```
Error Budget = (1 - SLO) * Total Requests

Example:
- SLO: 99.9% (0.999)
- Total requests/month: 10M
- Error budget: (1 - 0.999) * 10M = 10,000 errors/month
```

Track error budget burn rate:
- If burning too fast → freeze releases, fix reliability
- If headroom available → ship features faster

### 8. Chaos Engineering

**Goal:** Test system resilience by breaking things on purpose.

**Tools:** Chaos Mesh, Gremlin, or custom scripts

**Experiments:**
```yaml
# ops/chaos/pod-failure.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: api-pod-kill
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - multiplayer
    labelSelectors:
      app: api
  scheduler:
    cron: '@every 1h'
```

**Scenarios to test:**
- Random pod failures
- Network latency injection
- Database connection drops
- Redis eviction
- CPU/Memory stress

## Implementation Priority

### Phase 8.1: Foundation (Week 1-2)
- [x] Automated releases (DONE)
- [ ] Prometheus metrics collection
- [ ] Basic Grafana dashboards
- [ ] Structured JSON logging

### Phase 8.2: Observability (Week 3-4)
- [ ] Jaeger tracing integration
- [ ] ELK stack deployment
- [ ] Log aggregation pipelines
- [ ] Custom dashboards for all services

### Phase 8.3: Alerting (Week 5)
- [ ] Prometheus alert rules
- [ ] PagerDuty/Slack integration
- [ ] Runbook creation
- [ ] On-call rotation setup

### Phase 8.4: Performance (Week 6-7)
- [ ] Locust load testing framework
- [ ] Performance benchmarks
- [ ] Continuous performance testing in CI
- [ ] Performance regression detection

### Phase 8.5: Production Readiness (Week 8)
- [ ] Sentry error tracking
- [ ] SLO/SLI definitions
- [ ] Error budget tracking
- [ ] Chaos engineering experiments

## Success Metrics

After Phase 8 completion:

- ✅ **MTTR < 15 minutes** (Mean Time To Recovery)
- ✅ **MTTD < 5 minutes** (Mean Time To Detection)
- ✅ **99.9% uptime** SLO achieved
- ✅ **P95 latency < 500ms** for all endpoints
- ✅ **Zero unknown production issues** (all issues detected by monitoring)
- ✅ **100% of alerts have runbooks**
- ✅ **Performance tests in CI** catch regressions

## Cost Estimate

**Self-hosted (Docker Compose):** $0/month
- Prometheus: Free
- Grafana: Free
- Jaeger: Free
- ELK: Free

**Production (Cloud):** ~$300-500/month
- Grafana Cloud: $100/month
- Sentry: $80/month (25k errors)
- PagerDuty: $20/user/month
- Load testing infrastructure: $50-200/month

## Next Steps

1. **Start with metrics** - Prometheus + Grafana first
2. **Add tracing** - Jaeger for request flows
3. **Centralize logs** - ELK stack
4. **Set up alerts** - Don't wait for users to report issues
5. **Load test** - Know your limits
6. **Define SLOs** - Track reliability scientifically

**Ready to implement?** Let's start with Prometheus metrics!

---

**Questions?** See [CI-CD-SETUP.md](./CI-CD-SETUP.md) for CI/CD details.
