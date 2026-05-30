# AgentBreaker SDK

Python package for real-time budget enforcement in multi-agent AI systems.

## Installation

```bash
# Core (minimal dependencies)
pip install agentbreaker

# With PostgreSQL support
pip install agentbreaker[postgres]

# With LangChain integration
pip install agentbreaker[langchain]

# Development
pip install agentbreaker[dev]

# Load testing
pip install agentbreaker[load-test]
```

## Quick Start

### Decorator Pattern

```python
from agentbreaker import session, CircuitBreakerError

@session(
    session_id="agent-001",
    budget=10000,  # tokens
    team_id="engineering",
    task_total=50  # for velocity gating
)
async def run_agent():
    for task in tasks:
        # Budget check happens automatically
        result = await agent.step(task)
        # If budget exceeded, CircuitBreakerError is raised

try:
    await run_agent()
except CircuitBreakerError as e:
    print(f"Budget breach: {e.breach_type}")
```

### Context Manager Pattern

```python
from agentbreaker import session

async with session(session_id="agent-002", budget=5000) as sb:
    for i in range(100):
        result = await tool.invoke(input_data)
        # Manually record token usage
        sb.record(tool_name="calculator", tokens_used=result.usage.total_tokens)
        if i % 10 == 0:
            print(f"Progress: {sb.completion_ratio}%")
```

### LangChain Integration

```python
from langchain.agents import initialize_agent
from agentbreaker.adapters.langchain import AgentBreakerCallbackHandler

handler = AgentBreakerCallbackHandler(
    session_id="langchain-agent",
    budget=20000,
    team_id="data-science",
    task_total=100
)

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",
    callbacks=[handler],
    verbose=True
)

try:
    result = agent.run("Analyze the data and generate insights")
except Exception as e:
    print(f"Agent terminated: {e}")
```

## API Reference

### `session()`

Decorator and context manager for budget enforcement.

**Parameters:**
- `session_id: str` — Unique session identifier
- `budget: int` — Token budget for this session
- `team_id: str` — Team identifier (for escalation webhooks)
- `project_id: str | None` — Project identifier (optional)
- `task_total: int | None` — Expected number of tasks (for velocity gating)
- `store: BudgetStore | None` — Custom store backend (defaults to in-memory)

**Raises:**
- `BudgetExceededError` — Session exceeded token budget
- `LoopDetectedError` — Repetitive tool calls detected (likely infinite loop)
- `VelocityBreachError` — Spend rate outpacing task completion

### `CircuitBreakerError`

Base exception for all circuit breaker breaches.

**Attributes:**
- `breach_type: BreachType` — Type of breach (BUDGET_EXCEEDED, LOOP_DETECTED, VELOCITY_BREACH)
- `session_id: str` — Session ID
- `tokens_spent: int` — Total tokens spent before breach
- `tokens_remaining: int` — Tokens available at time of breach
- `message: str` — Human-readable explanation

### Models

All models are Pydantic schemas with validation.

```python
from agentbreaker.models import SessionBudget, ToolCallRecord, CircuitBreakerResult, BreachType

class SessionBudget(BaseModel):
    session_id: UUID4
    team_id: str
    project_id: str
    token_budget: int
    tokens_spent: int
    task_total: int | None
    tasks_completed: int
    created_at: datetime
    terminated_at: datetime | None
    termination_reason: BreachType | None

class ToolCallRecord(BaseModel):
    call_id: UUID4
    session_id: UUID4
    tool_name: str
    args_hash: str  # SHA-256 of canonical JSON args
    tokens_used: int
    timestamp: datetime

class CircuitBreakerResult(BaseModel):
    allowed: bool
    breach_type: BreachType | None
    tokens_remaining: int
    spend_ratio: float
    completion_ratio: float | None
    fingerprint_match: bool
    message: str
```

## Configuration

### Environment Variables

- `AGENTBREAKER_STORE` — Store backend: "memory" (dev) or "postgres" (prod)
- `AGENTBREAKER_DATABASE_URL` — PostgreSQL connection string (required for postgres store)
- `AGENTBREAKER_FINGERPRINT_WINDOW` — Number of recent calls to track for loop detection (default: 10)
- `AGENTBREAKER_REPEAT_THRESHOLD` — Number of repeats to flag as loop (default: 3)
- `AGENTBREAKER_VELOCITY_MULTIPLIER` — Spend/completion ratio threshold (default: 2.0)

### In-Memory Store (Development)

```python
from agentbreaker.store.memory import InMemoryStore

store = InMemoryStore()

@session(session_id="dev-agent", budget=1000, store=store)
async def run_agent():
    pass
```

### PostgreSQL Store (Production)

```python
from agentbreaker.store.postgres import PostgresStore

store = await PostgresStore.connect(
    database_url="postgresql+asyncpg://user:pass@localhost/agentbreaker"
)

@session(session_id="prod-agent", budget=10000, store=store)
async def run_agent():
    pass
```

## Performance

- **Latency per tool call**: < 2ms (atomic operations on PostgreSQL with row-level locking)
- **Throughput**: 500+ tool calls/second per API instance
- **Loop detection**: O(N) where N = fingerprint window size (default 10)
- **Memory overhead**: ~100 bytes per active session

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=agentbreaker --cov-report=html

# Specific test file
pytest tests/test_circuit.py -v

# Load testing
locust -f tests/load_test.py --host=http://localhost:8000
```

## License

Proprietary
