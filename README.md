# AgentBreaker — Real-Time Budget Enforcement + Loop Termination Engine for Multi-Agent Systems

## Problem

The $47K incident happened because monitoring is async and humans are slow. The only correct fix is **synchronous in-process enforcement** — the budget check must happen on the critical path of every tool call, not in a sidecar.

## Solution

AgentBreaker is a **production-grade circuit breaker** for AI agent frameworks. It enforces budget limits, detects infinite loops, and prevents cost overruns **in real time** with < 2ms overhead per tool call.

### Core Features

- **Atomic budget enforcement**: Every tool call is checked against available budget before execution (< 2ms latency)
- **Loop detection**: SHA-256 fingerprinting with subsequence matching catches simple repeats and rotating patterns
- **Velocity gating**: Pauses agents when spend rate outpaces task completion
- **Live ops dashboard**: War Room view of all active sessions, real-time burn rate tracking, manual session termination
- **Webhook escalation**: Integrates with Slack, PagerDuty, or custom alerting on budget breach
- **Multi-agent framework support**: LangChain, LangGraph, OpenAI Agents (adapters coming)

## Quick Start

### Install SDK

```bash
pip install agentbreaker
# With PostgreSQL support (production):
pip install agentbreaker[postgres]
# With LangChain integration:
pip install agentbreaker[langchain]
```

### Basic Usage (Decorator)

```python
from agentbreaker import session, CircuitBreakerError

@session(session_id="user-123", budget=10000, team_id="engineering")
async def run_agent_loop():
    while True:
        # Your agent loop
        result = await tool.invoke(args)
        # AgentBreaker automatically intercepts and checks budget
```

### With LangChain

```python
from agentbreaker.adapters.langchain import AgentBreakerCallbackHandler

handler = AgentBreakerCallbackHandler(
    session_id="user-123",
    budget=10000,
    team_id="engineering"
)

agent = initialize_agent(tools, llm, callbacks=[handler])

try:
    result = agent.run("solve this complex problem")
except CircuitBreakerError as e:
    print(f"Budget exceeded: {e.breach_type}")
```

### Start Full Stack (Development)

```bash
docker-compose up
# Postgres: localhost:5432
# API: http://localhost:8000
# Dashboard: http://localhost:3000
```

## Architecture

```
Agent Process
│
├── AgentBreaker Interceptor (decorator/middleware)
│   ├── Token meter — tracks spend per session/team/project
│   ├── Fingerprint engine — SHA-256 of last N (tool_name, args_hash) tuples
│   ├── Velocity gate — spend% vs completion% ratio evaluator
│   └── Circuit breaker — emits BudgetExceeded | LoopDetected | VelocityBreach
│
├── PostgreSQL budget store
│   ├── sessions, budgets, tool_call_log, fingerprint_window, alerts
│   └── Atomic DECREMENT via SELECT ... FOR UPDATE
│
└── FastAPI control plane
    ├── REST: session CRUD, budget config, manual kill
    ├── WebSocket: live burn rate stream per session
    └── Webhook: escalation callbacks on VelocityBreach
```

## Project Structure

```
agentbreaker/
├── sdk/                        # Python package (pip install agentbreaker)
│   ├── agentbreaker/
│   │   ├── core/              # Budget, circuit, fingerprint, velocity
│   │   ├── store/             # In-memory (dev) + PostgreSQL (prod)
│   │   ├── adapters/          # LangChain, LangGraph, etc.
│   │   └── models.py          # Pydantic schemas
│   └── tests/                 # Unit + load tests
│
├── api/                        # FastAPI control plane
│   ├── app/
│   │   ├── routers/           # Teams, sessions, alerts endpoints
│   │   ├── services/          # Escalation, metrics
│   │   ├── websocket.py       # Live burn rate WebSocket
│   │   ├── database.py        # AsyncSessionLocal, ORM models
│   │   ├── config.py          # Pydantic Settings
│   │   └── main.py            # FastAPI app + lifespan
│   ├── alembic/               # Database migrations
│   └── tests/                 # Integration tests
│
├── dashboard/                  # React ops console
│   ├── src/
│   │   ├── pages/             # WarRoom, SessionDetail, AlertsFeed
│   │   ├── hooks/             # useWebSocket
│   │   ├── components/        # Reusable UI
│   │   └── App.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
└── docker-compose.yml         # postgres + api + dashboard
```

## Development Timeline

- **Week 1–3**: Core enforcement engine (budget, fingerprint, velocity, circuit breaker)
- **Week 3–5**: FastAPI control plane (REST, WebSocket, escalation)
- **Week 5–7**: React ops dashboard (War Room, drill-down, alerts)
- **Week 8**: Hardening (load tests, PyPI packaging, ARCHITECTURE.md)

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Design decisions and tradeoffs
- [SDK README](sdk/README.md) — SDK API, examples, adapters
- [API README](api/README.md) — Control plane endpoints, WebSocket schema
- [Dashboard README](dashboard/README.md) — UI components, styling

## License

Proprietary (TBD)

## Contact

Team: [@ramannimje](https://github.com/ramannimje)
