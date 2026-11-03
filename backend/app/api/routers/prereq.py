"""
Prereq router  (FIXED)
──────────────────────

Root cause of the bug:
  The old router called submitPrereqQuiz which returned the already-graded
  result from state, but the graph's grade_quiz() + prereq_loop_router()
  were never actually called — so current_concept_index never incremented
  and next_concept_index was always 0 (same concept).

Fix:
  1. Grade the quiz directly via quiz_generator_node.grade_quiz().
  2. Read the result to decide passed/failed.
  3. If passed → increment current_concept_index in state manually,
     then run quiz_generator to produce the next concept's quiz.
  4. If failed → keep index, re-run quiz_generator for the same concept
     (fresh questions on retry).
  5. Return the correct next_concept_index, next_concept, and next_quiz.

Endpoints:
  POST /prereq/{session_id}/submit   → grade + advance
  GET  /prereq/{session_id}/status   → read-only status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from app.agents.graph import _quiz_generator_node
from app.agents.nodes.quiz_generator_node import prereq_loop_router
import app.api.store as store

logger = logging.getLogger(__name__)
router = APIRouter()


# ── models ─────────────────────────────────────────────────────────────────────

class SubmitQuizRequest(BaseModel):
    answers: List[str] = Field(
        description="One answer per question, in order. MCQ → 'A'/'B'/'C'/'D'. Code → exact string.",
        example=["A", "B", "setTasks", "missing key prop"],
    )


class QuizQuestionOut(BaseModel):
    type: str
    question: str
    options: Optional[List[str]] = None


class SubmitQuizResponse(BaseModel):
    graded_score: int
    passed: bool
    prereqs_complete: bool

    # populated when prereqs_complete is False
    next_concept: Optional[str]                      = None
    next_concept_index: Optional[int]                = None
    total_concepts: Optional[int]                    = None
    estimated_time: Optional[str]                    = None
    next_quiz: Optional[List[QuizQuestionOut]]       = None

    # populated when prereqs_complete is True
    message: Optional[str] = None


class PrereqStatusResponse(BaseModel):
    current_concept_index: int
    total_concepts: int
    quiz_results: list


# ── POST /prereq/{session_id}/submit ──────────────────────────────────────────

@router.post("/{session_id}/submit", response_model=SubmitQuizResponse)
def submit_quiz(session_id: str, body: SubmitQuizRequest):
    """
    Grade the current prereq quiz and advance to the next concept.

    Step-by-step:
      1. Load state from store.
      2. Call grade_quiz() — this scores the answers and updates
         quiz_results[-1].score / .passed in state.
         It also increments current_concept_index IF passed.
      3. Read the graded result.
      4. If passed and more concepts remain → run quiz_generator_node.run()
         to generate the quiz for the NOW-CURRENT concept (the incremented index).
      5. Return the full response with the correct next_concept_index.
    """
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    prereqs = state.get("prerequisites", [])
    if not prereqs:
        raise HTTPException(status_code=400, detail="No prerequisites found in session.")

    # ── Step 1: grade the quiz ────────────────────────────────────────────────
    try:
        state = _quiz_generator_node.grade_quiz(state, body.answers)
    except Exception as e:
        logger.error(f"grade_quiz error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # grade_quiz() has already incremented current_concept_index if passed
    graded_result = state["quiz_results"][-1]
    passed        = graded_result["passed"]
    score         = graded_result["score"]
    new_index     = state["current_concept_index"]   # authoritative index post-grade
    total         = len(prereqs)

    logger.info(
        f"submit_quiz: session={session_id} passed={passed} "
        f"score={score} new_index={new_index} total={total}"
    )

    # ── Step 2: all prereqs done ──────────────────────────────────────────────
    if new_index >= total:
        store.set(session_id, state)
        return SubmitQuizResponse(
            graded_score=score,
            passed=passed,
            prereqs_complete=True,
            message=(
                "All prerequisite concepts cleared! "
                "Please describe your plan for building the project."
            ),
        )

    # ── Step 3: generate quiz for the next (or same, on fail) concept ─────────
    # new_index already points to the correct concept:
    #   - on PASS  → grade_quiz incremented it, so it's the next concept
    #   - on FAIL  → grade_quiz left it unchanged, so it's the same concept (retry)
    try:
        state = _quiz_generator_node.run(state)
    except Exception as e:
        logger.error(f"quiz_generator error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    # The freshly generated quiz is the last entry in quiz_results
    next_quiz_result = state["quiz_results"][-1]
    next_prereq      = prereqs[new_index]

    return SubmitQuizResponse(
        graded_score=score,
        passed=passed,
        prereqs_complete=False,
        next_concept=next_prereq["concept"],
        next_concept_index=new_index,           # correct index after grade_quiz
        total_concepts=total,
        estimated_time=next_prereq.get("estimated_time", "1 day"),
        next_quiz=[
            QuizQuestionOut(
                type=q["type"],
                question=q["question"],
                options=q.get("options"),
            )
            for q in next_quiz_result["questions"]
        ],
    )


# ── GET /prereq/{session_id}/status ───────────────────────────────────────────

@router.get("/{session_id}/status", response_model=PrereqStatusResponse)
def prereq_status(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return PrereqStatusResponse(
        current_concept_index=state["current_concept_index"],
        total_concepts=len(state.get("prerequisites", [])),
        quiz_results=[
            {
                "concept": r["concept"],
                "score":   r["score"],
                "passed":  r["passed"],
            }
            for r in state.get("quiz_results", [])
        ],
    )