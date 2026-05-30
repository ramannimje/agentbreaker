# Architecture & Design Decisions

## Principal Engineer Decision Log

This document captures key architectural decisions, tradeoffs, and the reasoning behind AgentBreaker's design.

---

## 1. Atomic SQL Decrement vs Redis INCR

**Decision**: Use PostgreSQL `SELECT ... FOR UPDATE` for atomic budget decrement, not Redis INCR.

### Rationale

Budget enforcement is a **strong consistency invariant**. If two concurrent tool calls read the same budget balance and both succeed, the session has overspent — the entire enforcement layer fails.

- **PostgreSQL approach**:
  - `SELECT tokens_spent FROM sessions WHERE session_id=$1 FOR UPDATE` (row-level lock)
  - Check: `tokens_spent + new_tokens <= token_budget`
  - `UPDATE sessions SET tokens_spent = tokens_spent + $1 WHERE session_id=$2`
  - Guarantees: Linearizability. Only one process can hold the lock.

- **Redis approach**:
  - `INCR` is atomic on a single key, but the budget ceiling check must happen *before* the INCR
  - Naive: Read balance, check, then INCR → race condition (two processes both see old balance)
  - Correct: Use Lua scripting or Redis transactions, but adds complexity and still has client-side timeout risks

### Tradeoff

- **Postgres cost**: ~2–5ms per call (network + locking overhead)
- **Redis cost**: <1ms per call, but complex client-side orchestration required

**Verdict**: Correctness > speed. Budget breach costs $47K. A few extra milliseconds per call is acceptable.

### Future Scaling

At >10k concurrent sessions, consider **sharding by session_id** to reduce lock contention. Each shard maintains its own budget state.

---

## 2. SHA-256 Fingerprinting vs Simhash for Loop Detection

**Decision**: Use SHA-256 exact match on `(tool_name:args_hash)` tuples, not simhash (fuzzy matching).

### Rationale

Loop detection must flag **true loops with zero false positives**. A loop is defined as: repetition of identical tool calls (same tool, same arguments).

- **Exact match (SHA-256)**:
  - Fingerprint = SHA-256(`tool_1:args_1|tool_2:args_2|...`)
  - Detects: Simple repeats (calc→calc→calc), rotating patterns (A→B→A→B)
  - False positives: None (if inputs are identical, it IS a loop invariant)
  - False negatives: Won't catch "similar but different" patterns (e.g., user_id incremented by 1)

- **Simhash (fuzzy)**:
  - Computes Hamming distance between fingerprints
  - Detects: Similarity within a threshold
  - False positives: Legitimate variations (user_id=123 vs user_id=124) might flag as loops
  - False negatives: Reduced (catches "almost" loops)

### Why Exact is Correct

If tool A with args X has been called 5 times in a row, *that is a loop*. Agent made no progress. The args being identical is not a bug in detection—it's the whole point.

If tool A is called with user_id=123, then user_id=124, that's **different work** and should not flag as a loop.

### Implementation Details

- Fingerprint window size: Configurable per team (default: 10)
- Repeat threshold: Configurable per team (default: 3)
- Subsequence matching: Detect rotating loops by finding recurring patterns of length 2..N/2 in the fingerprint sequence

### Cost

- **Computation**: SHA-256 per fingerprint is O(1), negligible cost
- **Storage**: ~100 bytes per fingerprint window (10 calls × ~10 bytes each)

---

## 3. WebSocket vs Server-Sent Events (SSE) for Live Dashboard Stream

**Decision**: Use WebSocket (bidirectional) instead of SSE (unidirectional).

### Rationale

The dashboard is not just a **passive observer**. It must send commands back to the API:

- Manual session kill: `POST /sessions/{id}/kill`
- Budget adjustment: `PATCH /sessions/{id}/budget`
- Acknowledge alerts: `PATCH /alerts/{id}/acknowledge`

With WebSocket, these commands can be multiplexed over the same connection, reducing connection overhead.

- **WebSocket approach**:
  - Client → Server: Commands (kill, adjust budget)
  - Server → Client: Burn updates, alerts
  - Bidirectional, persistent connection

- **SSE approach**:
  - Server → Client: Burn updates only (unidirectional)
  - Client → Server: Commands via separate HTTP requests
  - Higher connection overhead for command path

### Tradeoff

- **WebSocket cost**: Stateful connections consume more memory at scale. 10k concurrent ops engineers = 10k open sockets.
- **SSE cost**: Less memory, but more round trips for commands.

**Verdict**: For MVP (< 100 concurrent ops engineers), WebSocket is superior. At scale (> 10k), could switch to SSE + polling with service worker for a more stateless API layer.

### Fallback Plan

If WebSocket proves problematic in production, the API already exposes REST equivalents. Dashboard can fall back to:
```javascript
// WebSocket fails, use REST polling
setInterval(async () => {
  const session = await fetch(`/api/sessions/${id}`).then(r => r.json());
  updateUI(session);
}, 1000);
```

---

## 4. Zero Mandatory Dependencies for SDK

**Decision**: SDK requires only `pydantic` and `httpx`. PostgreSQL and LangChain are optional extras.

### Rationale

**Adoption depends on frictionless integration.** If a team already uses Redis and SQLite elsewhere, forcing PostgreSQL creates unnecessary churn and conflicts.

- **Zero mandatory approach**:
  - Core: Pydantic (validation), httpx (async HTTP for future webhooks)
  - Optional: `agentbreaker[postgres]` adds SQLAlchemy + asyncpg
  - Optional: `agentbreaker[langchain]` adds langchain libraries
  - **Benefit**: Teams can integrate without dependency conflicts

- **Alternative** (everything included):
  - `pip install agentbreaker` brings all deps
  - **Benefit**: Simpler packaging
  - **Cost**: Higher chance of version conflicts with existing projects

### Implementation Cost

Dual-interface abstraction (memory store + postgres store) adds ~15–20% code complexity, but separates concerns and enables true optionality.

```python
# User chooses store at import time
if use_postgres:
    from agentbreaker.store.postgres import PostgresStore
    store = await PostgresStore.connect(db_url)
else:
    from agentbreaker.store.memory import InMemoryStore
    store = InMemoryStore()

@session(session_id="...", budget=1000, store=store)
async def run_agent():
    pass
```

---

## 5. Velocity Gate Pauses Rather Than Terminates

**Decision**: On velocity breach, pause the session and emit an escalation webhook, allowing humans to decide the next action.

### Rationale

Spend rate suddenly spikes for legitimate reasons:
- Switched to a more capable (expensive) model
- Working on a particularly complex task
- Legitimate spike in tool usage for one large task

**Terminating automatically would:**
- Lose expensive context (agent state, progress)
- Violate SLA guarantees
- Prevent legitimate business operations

**Pausing + escalation allows:**
- Ops team alerted within 1 second (webhook timeout is enforced)
- Humans review the spike (is it legitimate?)
- Options: Resume, increase budget, or terminate with context preserved

### Escalation Guarantee

1. Velocity breach detected
2. Webhook POST to team's escalation URL within 1 second (timeout enforced)
3. Escalation service retries with exponential backoff (up to 3x) if first attempt fails
4. Ops team has 5 minutes to resume or terminate session
5. If no action taken after 5 min, auto-terminate (configurable per team)

### Exception: Absolute Budget Ceiling

Unlike velocity gate, if session hits absolute budget ceiling:
- **Immediate termination**, no grace period
- Prevents accidental $50K overruns
- The invariant is: `tokens_spent <= token_budget` always

---

## 6. PostgreSQL Schema Design: Row-Level Locking & Indexes

**Decision**: Use `SELECT ... FOR UPDATE` on sessions table for atomic decrement; add strategic indexes for query performance.

### Schema

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    team_id UUID REFERENCES teams(team_id),
    project_id TEXT NOT NULL,
    token_budget INT NOT NULL,
    tokens_spent INT NOT NULL DEFAULT 0,
    task_total INT,
    tasks_completed INT DEFAULT 0,
    status TEXT DEFAULT 'active',
    termination_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    terminated_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_team_created
    ON sessions(team_id, created_at DESC);

CREATE INDEX idx_sessions_status
    ON sessions(status, tokens_spent DESC);

CREATE TABLE tool_call_log (
    call_id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id),
    tool_name TEXT NOT NULL,
    args_hash TEXT NOT NULL,
    tokens_used INT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tool_call_log_session_time
    ON tool_call_log(session_id, timestamp DESC);
```

### Atomic Decrement Implementation

```python
async def check_and_record(self, session_id, tokens_used):
    async with self.db.begin():  # Transaction
        # Lock the row, get current state
        result = await self.db.execute(
            text("""
                SELECT tokens_spent, token_budget, status
                FROM sessions
                WHERE session_id = :sid
                FOR UPDATE
            """),
            {"sid": session_id}
        )
        tokens_spent, budget, status = result.first()
        
        # Check breach
        if status != 'active':
            raise SessionTerminated()
        if tokens_spent + tokens_used > budget:
            raise BudgetExceededError()
        
        # Atomic update (no race condition possible within transaction)
        await self.db.execute(
            text("UPDATE sessions SET tokens_spent = tokens_spent + :t WHERE session_id = :sid"),
            {"t": tokens_used, "sid": session_id}
        )
        
        # Record tool call
        await self.db.execute(
            text("INSERT INTO tool_call_log (...) VALUES (...)"),
            {...}
        )
```

---

## 7. Monorepo Structure

**Decision**: Single git repository with three subdirectories (sdk/, api/, dashboard/) over separate repos.

### Rationale

- **Unified versioning**: Core API changes propagate to dashboard + SDK simultaneously
- **Single CI/CD**: One GitHub Actions workflow builds and tests all components
- **Contributor onboarding**: Everything in one place

### Alternative (Separate Repos)

- ✅ Cleaner separation of concerns
- ❌ Version synchronization complexity (SDK v0.1.0 vs API v0.2.0 → compatibility issues)
- ❌ Harder to trace cross-component bugs

**Verdict**: Monorepo for MVP. If scaling to 20+ engineers, could split later with clear versioning strategy.

---

## 8. Fingerprint Window Size Configuration

**Decision**: Make fingerprint window size (number of recent calls to track) configurable per team.

### Rationale

One team's heuristic breaks another's workflow:
- **Team A** (test suite): Legitimately cycles through 5–10 setup tool calls
- **Team B** (production agent): Any repeated call > 3x is likely a bug

### Configuration

```python
POST /teams
{
  "team_id": "engineering",
  "name": "Engineering Team",
  "fingerprint_window_size": 15,  # override default (10)
  "repeat_threshold": 4,           # override default (3)
  "velocity_multiplier": 2.0
}
```

---

## 9. Load Testing Strategy

**Decision**: Target 500 tool calls/sec per API instance with p99 < 5ms latency.

### Why 500/sec?

Based on industry benchmarks:
- Average agent session: 10–50 tool calls
- Concurrent sessions per API: 50–100
- Calls per session: 10 calls/sec during active work
- Peak load: 500 calls/sec = 50 sessions × 10 calls/sec (reasonable for single-instance ops)

### Verification

```bash
# Load test
locust -f tests/load_test.py --host=http://localhost:8000 --users=500 --spawn-rate=50

# Expected:
# - Requests/sec: > 500
# - p99 latency: < 5ms
# - p99.9 latency: < 10ms
# - Errors: 0
# - Budget overruns: 0
```

---

## 10. Why Async-First (asyncio)

**Decision**: API and SDK are async-first (asyncio), not threaded.

### Rationale

- **Tool calls are I/O-bound**: Network calls, DB queries
- **Async avoids GIL**: Python threading is GIL-limited; asyncio is not
- **Concurrent connections**: 100 concurrent WebSocket connections require async, not threading
- **Scalability**: 500 calls/sec needs concurrency, not threads

### Trade-off

- **Complexity**: Async/await syntax more complex than sync
- **Debugging**: Stack traces can be harder to follow
- **Adoption**: Requires async-aware frameworks (LangChain has async support, but not all tools)

**Verdict**: Non-negotiable for production. Framework overhead is worth the concurrency gain.

---

## 11. Pydantic for Validation (Not Marshmallow)

**Decision**: Use Pydantic v2 for all API request/response validation, not Marshmallow.

### Rationale

- **Pydantic v2** is the FastAPI standard
- **Performance**: ~10x faster than Marshmallow for serialization
- **Type hints**: Integrates seamlessly with Python 3.10+ type system
- **Validation**: More powerful custom validators

---

## Future Considerations (Post-MVP)

1. **Observability**: Add distributed tracing (OpenTelemetry) and central logging (Grafana Loki) at scale
2. **Sharding**: Partition budget store by session_id for horizontal scaling
3. **Multi-region**: Replicate budget state across regions with eventual consistency
4. **Mobile**: Native ops dashboards (iOS/Android) for ops-on-call scenarios
5. **Advanced analytics**: Historical spend trends, team budgets, cost forecasting (deferred to v1.1)

