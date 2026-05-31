GitHub Actions secrets for AgentBreaker CI

Set `AGENTBREAKER_DATABASE_URL` if you want CI to run integration tests against a managed Postgres instance instead of spinning up ephemeral containers via `testcontainers`.

Value format (example):

postgresql://user:password@host:5432/dbname

Notes:
- If the secret is not set, CI tests will use `testcontainers` to start an ephemeral Postgres (requires Docker on the runner).
- To add the secret: go to your repository Settings → Secrets and variables → Actions → New repository secret.
