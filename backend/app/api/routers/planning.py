"""
Planning router
───────────────
POST /planning/{id}/approach  → analyzer_node + roadmap_node directly
GET  /planning/{id}/roadmap   → return roadmap
GET  /planning/{id}/analysis  → return analysis
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from app.agents.graph import analyzer_node, roadmap_node
import app.api.store as store

logger = logging.getLogger(__name__)
router = APIRouter()


# ── models ────────────────────────────────────────────────────────────────────

class SubmitApproachRequest(BaseModel):
    approach: str = Field(min_length=50)


class WeekSummary(BaseModel):
    week_number: int
    start_date:  str
    end_date:    str
    theme:       str
    goal:        str
    topics:      List[str]
    deliverable: str
    difficulty:  str


class MilestoneSummary(BaseModel):
    week:        int
    description: str


class RoadmapResponse(BaseModel):
    total_weeks: int
    weeks:       List[WeekSummary]
    milestones:  List[MilestoneSummary]


class AnalysisGap(BaseModel):
    point:      str
    detail:     str
    suggestion: str


class AnalysisPositive(BaseModel):
    point:  str
    detail: str


class AnalysisResponse(BaseModel):
    overall_understanding:    str
    positives:                List[AnalysisPositive]
    gaps:                     List[AnalysisGap]
    recommended_focus_areas:  List[str]


class SubmitApproachResponse(BaseModel):
    analysis: AnalysisResponse
    roadmap:  RoadmapResponse


# ── routes ────────────────────────────────────────────────────────────────────

@router.post("/{session_id}/approach", response_model=SubmitApproachResponse)
def submit_approach(session_id: str, body: SubmitApproachRequest):
    """
    1. Write student_approach into state.
    2. Run analyzer_node  → produces positives, gaps, focus areas.
    3. Run roadmap_node   → produces week-by-week plan.
    4. Save and return.

    No graph stream — nodes called directly in order.
    """
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if state.get("roadmap"):
        raise HTTPException(status_code=409, detail="Roadmap already generated.")

    # inject student approach
    state = {**state, "student_approach": body.approach}

    try:
        # Step 1: analyze the approach
        state = analyzer_node.run(state)

        # Step 2: build the roadmap from the analysis
        state = roadmap_node.run(state)

    except Exception as e:
        logger.error(f"submit_approach error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    store.set(session_id, state)

    return SubmitApproachResponse(
        analysis=AnalysisResponse(**state["analysis"]),
        roadmap=RoadmapResponse(**state["roadmap"]),
    )


@router.get("/{session_id}/roadmap", response_model=RoadmapResponse)
def get_roadmap(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("roadmap"):
        raise HTTPException(status_code=404, detail="Roadmap not yet generated.")
    return RoadmapResponse(**state["roadmap"])


@router.get("/{session_id}/analysis", response_model=AnalysisResponse)
def get_analysis(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.get("analysis"):
        raise HTTPException(status_code=404, detail="Analysis not yet generated.")
    return AnalysisResponse(**state["analysis"])