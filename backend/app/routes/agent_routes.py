"""
Debug/inspection endpoints for the agent nodes.

These are not part of the student flow — they just let the teacher or a
developer poke a single node in isolation. Useful during prompt tuning.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from app.agents.graph import prerequisite_node, roadmap_node, analyzer_node

router = APIRouter()


class NodeInvokeRequest(BaseModel):
    state: Dict[str, Any]


@router.post("/prerequisite/run")
def run_prerequisite(body: NodeInvokeRequest):
    try:
        return prerequisite_node.run(body.state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyzer/run")
def run_analyzer(body: NodeInvokeRequest):
    try:
        return analyzer_node.run(body.state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roadmap/run")
def run_roadmap(body: NodeInvokeRequest):
    try:
        return roadmap_node.run(body.state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
