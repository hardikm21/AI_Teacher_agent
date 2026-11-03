"""
Simple in-memory session store.

In production replace this with:
  - Redis  : store.py wraps redis-py with JSON serialisation
  - Postgres: store.py wraps asyncpg with a sessions table

The rest of the API layer does not care — it only calls get/set/delete.
"""
from typing import Dict, Optional
from app.agents.state import AgentState

_store: Dict[str, AgentState] = {}


def get(session_id: str) -> Optional[AgentState]:
    return _store.get(session_id)


def set(session_id: str, state: AgentState) -> None:
    _store[session_id] = state


def delete(session_id: str) -> None:
    _store.pop(session_id, None)


def exists(session_id: str) -> bool:
    return session_id in _store