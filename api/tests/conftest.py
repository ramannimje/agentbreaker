import os
import pytest

from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_url():
    url = os.getenv("AGENTBREAKER_DATABASE_URL")
    if url:
        return url
    # start ephemeral postgres via testcontainers
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url()
        os.environ["AGENTBREAKER_DATABASE_URL"] = url
        yield url