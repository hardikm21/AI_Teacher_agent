"""
Teacher/admin dashboard endpoints — aggregate view across live sessions.
"""
from fastapi import APIRouter, Depends

import app.api.store as store
from app.auth import require_role
from app.routes import project_routes

router = APIRouter()


@router.get("", dependencies=[Depends(require_role("teacher"))])
def dashboard():
    """
    Return an aggregate snapshot: project catalog size, active sessions, and
    per-session progress. Cheap enough to recompute on every request for the
    demo's in-memory store.
    """
    sessions = []
    for sid, state in store._store.items():
        total = len(state.get("roadmap", {}).get("weeks", []) or [])
        sessions.append({
            "session_id": sid,
            "user_id":    state.get("user_id"),
            "project":    (state.get("project") or {}).get("name"),
            "week":       state.get("current_week", 0),
            "total_weeks": total,
            "score":      state.get("weekly_score_display"),
            "completed":  state.get("project_complete", False),
        })

    return {
        "projects":         len(project_routes._projects),
        "active_sessions":  len(sessions),
        "completed":        sum(1 for s in sessions if s["completed"]),
        "sessions":         sessions,
    }
