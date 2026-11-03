"""
Sessions router
───────────────
POST /sessions/start   → run prerequisite_node + quiz_generator_node directly
GET  /sessions/{id}    → return full state
DELETE /sessions/{id}  → clean up
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import logging

from app.agents.graph import (
    get_initial_state,
    prerequisite_node,
    quiz_generator_node,
)
import app.api.store as store

logger = logging.getLogger(__name__)
router = APIRouter()


# ── models ────────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    user_id:       str
    project:       dict  = Field(example={"name": "AI Task Manager", "description": "..."})
    known_stack:   List[str]
    unknown_stack: List[str]
    start_date:    str
    end_date:      str
    repo_url:      str
    github_branch: str               = "main"
    blackout_dates: Optional[List[str]] = None


class QuizQuestionOut(BaseModel):
    type:    str
    question: str
    options: Optional[List[str]] = None


class StartSessionResponse(BaseModel):
    session_id:     str
    concept:        str
    concept_index:  int
    total_concepts: int
    estimated_time: str
    quiz:           List[QuizQuestionOut]


# ── routes ────────────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartSessionResponse)
def start_session(body: StartSessionRequest):
    """
    1. Build zero-state.
    2. Run prerequisite_node  → generates the concept list.
    3. Run quiz_generator_node → generates quiz for concept 0.
    4. Save state, return first quiz.
    """
    session_id = str(uuid.uuid4())
    state = get_initial_state(
        user_id=body.user_id,
        project=body.project,
        known_stack=body.known_stack,
        unknown_stack=body.unknown_stack,
        start_date=body.start_date,
        end_date=body.end_date,
        repo_url=body.repo_url,
        github_branch=body.github_branch,
        blackout_dates=body.blackout_dates,
    )

    try:
        # Step 1: generate prerequisite concepts
        state = prerequisite_node.run(state)

        # Step 2: generate quiz for concept 0
        state = quiz_generator_node.run(state)

    except Exception as e:
        logger.error(f"start_session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    prereqs = state["prerequisites"]
    idx     = state["current_concept_index"]   # 0
    quiz    = state["quiz_results"][-1]

    return StartSessionResponse(
        session_id=session_id,
        concept=prereqs[idx]["concept"],
        concept_index=idx,
        total_concepts=len(prereqs),
        estimated_time=prereqs[idx].get("estimated_time", "1 day"),
        quiz=[
            QuizQuestionOut(type=q["type"], question=q["question"], options=q.get("options"))
            for q in quiz["questions"]
        ],
    )


@router.get("/{session_id}")
def get_session(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


@router.delete("/{session_id}")
def delete_session(session_id: str):
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    store.delete(session_id)
    return {"deleted": session_id}