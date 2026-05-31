"""Factory helpers to create a store backend from environment/config."""
from __future__ import annotations

import os
from typing import Optional

from agentbreaker.store.memory import InMemoryStore

try:
    from agentbreaker.store.postgres import PostgresStore
except Exception:  # pragma: no cover - optional dependency
    PostgresStore = None


async def create_store_from_env(database_url: Optional[str] = None):
    store_type = os.getenv("AGENTBREAKER_STORE", "memory")
    if store_type == "postgres":
        dburl = database_url or os.getenv("AGENTBREAKER_DATABASE_URL")
        if not dburl:
            raise RuntimeError("AGENTBREAKER_DATABASE_URL must be set for postgres store")
        if PostgresStore is None:
            raise RuntimeError("PostgresStore optional dependency not installed")
        return await PostgresStore.connect(dburl)
    # default memory
    return InMemoryStore()
