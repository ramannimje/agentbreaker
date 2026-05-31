-- Initial schema for AgentBreaker
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS teams (
    team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    default_budget INT NOT NULL DEFAULT 100000,
    velocity_multiplier FLOAT NOT NULL DEFAULT 2.0,
    escalation_webhook TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(team_id),
    project_id TEXT NOT NULL,
    token_budget INT NOT NULL,
    tokens_spent INT NOT NULL DEFAULT 0,
    task_total INT,
    tasks_completed INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    termination_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tool_call_log_session_time ON tool_call_log(session_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS tool_call_log (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id),
    tool_name TEXT NOT NULL,
    args_hash TEXT NOT NULL,
    tokens_used INT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id),
    breach_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ
);
