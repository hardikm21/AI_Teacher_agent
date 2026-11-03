"""
Weekly router
─────────────
POST /weekly/{id}/start        → task_generator_node directly
POST /weekly/{id}/check        → completion_check_node directly
GET  /weekly/{id}/quiz         → task_quiz_node directly
POST /weekly/{id}/quiz/submit  → task_quiz_node.grade_quiz() + evaluator_node directly
GET  /weekly/{id}/tasks        → return current tasks
GET  /weekly/{id}/score        → return latest score
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from app.agents.graph import (
    task_generator_node,
    completion_check_node,
    task_quiz_node,
    evaluator_node,
)
import app.api.store as store

logger = logging.getLogger(__name__)
router = APIRouter()


# ── models ────────────────────────────────────────────────────────────────────

class TaskSubmission(BaseModel):
    github_folder:  str
    filename:       str
    commit_message: str


class TaskOut(BaseModel):
    day:             int
    title:           str
    description:     str
    steps:           List[str]
    submission:      TaskSubmission
    estimated_hours: int


class WeekTasksResponse(BaseModel):
    week_number: int
    theme:       str
    goal:        str
    difficulty:  str
    tasks:       List[TaskOut]


class CheckCompletionResponse(BaseModel):
    week_number: int
    completed:   bool
    reason:      str
    next_step:   str   # "task_quiz" | "retry_tasks"


class SubmitTaskQuizRequest(BaseModel):
    answers: List[str] = Field(
        description="Answers in question order. MCQ → 'A'/'B'/'C'/'D'. Code/text → string."
    )


class EvaluationBreakdown(BaseModel):
    completion_points:    int
    quiz_points:          int
    reflection_points:    int
    difficulty_adjustment: int


class EvaluationFeedback(BaseModel):
    strength:      str
    improvement:   str
    message:       str
    next_week_tip: str


class EvaluationResponse(BaseModel):
    week_number:     int
    score:           float
    score_display:   float
    breakdown:       Optional[EvaluationBreakdown] = None
    feedback:        EvaluationFeedback
    project_complete: bool
    next_week:       Optional[int] = None


class QuizQuestionOut(BaseModel):
    type:     str
    question: str
    options:  Optional[List[str]] = None


class TaskQuizResponse(BaseModel):
    week_number: int
    concept:     str
    questions:   List[QuizQuestionOut]


# ── routes ────────────────────────────────────────────────────────────────────

@router.post("/{session_id}/start", response_model=WeekTasksResponse)
def start_week(session_id: str):
    """Generate 5 daily tasks for the current week."""
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("roadmap"):
        raise HTTPException(status_code=409, detail="Roadmap not generated yet.")
    if state.get("project_complete"):
        raise HTTPException(status_code=410, detail="Project is already complete.")

    try:
        state = task_generator_node.run(state)
    except Exception as e:
        logger.error(f"start_week error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    current_week = state["current_week"]
    week_plan    = state["roadmap"]["weeks"][current_week - 1]

    return WeekTasksResponse(
        week_number=current_week,
        theme=week_plan["theme"],
        goal=week_plan["goal"],
        difficulty=week_plan.get("difficulty", "medium"),
        tasks=[TaskOut(**t) for t in state["weekly_tasks"]],
    )


@router.post("/{session_id}/check", response_model=CheckCompletionResponse)
def check_completion(session_id: str):
    """Run completion check against GitHub."""
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("weekly_tasks"):
        raise HTTPException(status_code=409, detail="No tasks generated yet.")

    repo_url = state.get("repo_url", "")
    branch   = state.get("github_branch", "main")

    if not repo_url:
        raise HTTPException(status_code=400, detail="repo_url not set in session.")

    try:
        state = completion_check_node.run(state, repo_url=repo_url, branch=branch)
    except Exception as e:
        logger.error(f"check_completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    completed = state.get("completion_status", False)
    return CheckCompletionResponse(
        week_number=state["current_week"],
        completed=completed,
        reason=state.get("completion_reason", ""),
        next_step="task_quiz" if completed else "retry_tasks",
    )


@router.post("/{session_id}/override-complete", response_model=CheckCompletionResponse)
def override_complete(session_id: str):
    """
    Demo/offline override: mark the current week as completed without running
    the GitHub check. Useful when there is no real repo yet (live demos, or
    the student is using a sandbox branch the API can't see).
    """
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("weekly_tasks"):
        raise HTTPException(status_code=409, detail="No tasks generated yet.")

    state = {
        **state,
        "completion_status": True,
        "completion_reason": "Manually marked complete (demo override).",
    }
    store.set(session_id, state)

    return CheckCompletionResponse(
        week_number=state["current_week"],
        completed=True,
        reason=state["completion_reason"],
        next_step="task_quiz",
    )


@router.get("/{session_id}/quiz", response_model=TaskQuizResponse)
def get_task_quiz(session_id: str):
    """Generate and return the task quiz for the current week."""
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("completion_status"):
        raise HTTPException(status_code=409, detail="Completion check not passed yet.")

    try:
        state = task_quiz_node.run(state)
    except Exception as e:
        logger.error(f"get_task_quiz error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    quiz = state["task_quiz_results"][-1]
    return TaskQuizResponse(
        week_number=state["current_week"],
        concept=quiz["concept"],
        questions=[
            QuizQuestionOut(type=q["type"], question=q["question"], options=q.get("options"))
            for q in quiz["questions"]
        ],
    )


@router.post("/{session_id}/quiz/submit", response_model=EvaluationResponse)
def submit_task_quiz(session_id: str, body: SubmitTaskQuizRequest):
    """Grade task quiz + run evaluator."""
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("task_quiz_results"):
        raise HTTPException(status_code=409, detail="No task quiz generated yet.")

    try:
        # Grade quiz
        state = task_quiz_node.grade_quiz(state, body.answers)

        # Evaluate the week
        state = evaluator_node.run(state)

    except Exception as e:
        logger.error(f"submit_task_quiz error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    # evaluated week is current_week - 1 (evaluator increments current_week)
    evaluated_week = state["current_week"] - 1
    week_plan      = state["roadmap"]["weeks"][evaluated_week - 1]
    feedback       = state["evaluation_feedback"] or {}
    breakdown_raw  = state.get("evaluation_breakdown")

    return EvaluationResponse(
        week_number=evaluated_week,
        score=state["weekly_score"],
        score_display=state["weekly_score_display"],
        breakdown=EvaluationBreakdown(**breakdown_raw) if breakdown_raw else None,
        feedback=EvaluationFeedback(**feedback),
        project_complete=state.get("project_complete", False),
        next_week=state["current_week"] if not state.get("project_complete") else None,
    )


@router.get("/{session_id}/tasks", response_model=WeekTasksResponse)
def get_tasks(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("weekly_tasks"):
        raise HTTPException(status_code=404, detail="No tasks generated yet.")

    current_week = state["current_week"]
    week_plan    = state["roadmap"]["weeks"][current_week - 1]

    return WeekTasksResponse(
        week_number=current_week,
        theme=week_plan["theme"],
        goal=week_plan["goal"],
        difficulty=week_plan.get("difficulty", "medium"),
        tasks=[TaskOut(**t) for t in state["weekly_tasks"]],
    )


@router.get("/{session_id}/score", response_model=EvaluationResponse)
def get_score(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.get("weekly_score") is None:
        raise HTTPException(status_code=404, detail="No evaluation yet.")

    evaluated_week = state["current_week"] - 1
    week_plan      = state["roadmap"]["weeks"][evaluated_week - 1]
    feedback       = state["evaluation_feedback"] or {}
    breakdown_raw  = state.get("evaluation_breakdown")

    return EvaluationResponse(
        week_number=evaluated_week,
        score=state["weekly_score"],
        score_display=state["weekly_score_display"],
        breakdown=EvaluationBreakdown(**breakdown_raw) if breakdown_raw else None,
        feedback=EvaluationFeedback(**feedback),
        project_complete=state.get("project_complete", False),
        next_week=state["current_week"] if not state.get("project_complete") else None,
    )