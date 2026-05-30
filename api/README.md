# API Control Plane

FastAPI control plane for AgentBreaker budget enforcement engine.

## Endpoints

### Teams

- `POST /teams` — Create a new team
- `GET /teams/{team_id}` — Get team configuration
- `PATCH /teams/{team_id}` — Update team settings

### Sessions

- `POST /sessions` — Register new session
- `GET /sessions/{session_id}` — Get session state
- `GET /teams/{team_id}/sessions` — List all sessions for team
- `POST /sessions/{session_id}/kill` — Manual hard stop
- `PATCH /sessions/{session_id}/budget` — Adjust budget mid-session
- `GET /sessions/{session_id}/trace` — Full tool call log with fingerprints

### Alerts

- `GET /alerts` — List unacknowledged alerts
- `PATCH /alerts/{alert_id}/acknowledge` — Mark alert as read

### WebSocket

- `GET /ws/sessions/{session_id}` — Live burn rate for single session
- `GET /ws/sessions` — Live burn rate for all sessions

### Health

- `GET /health` — Basic health check
- `GET /health/ready` — Readiness probe (DB connected)

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://agentbreaker:password@localhost:5432/agentbreaker"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

## Architecture

See [ARCHITECTURE.md](../ARCHITECTURE.md) for design decisions.
