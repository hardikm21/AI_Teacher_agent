"""
Teacher-facing project catalog.

This is intentionally backed by an in-memory dict so the demo runs without
any DB. Swap for a real store by replacing `_projects` with something that
talks to Postgres — the router surface doesn't change.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List

from app.auth import require_role
from app.models.project import Project, ProjectCreate

router = APIRouter()

_projects: Dict[str, Project] = {}


@router.get("", response_model=List[Project])
def list_projects():
    return list(_projects.values())


@router.post("", response_model=Project, status_code=201,
             dependencies=[Depends(require_role("teacher"))])
def create_project(body: ProjectCreate):
    project = Project(**body.model_dump())
    _projects[project.id] = project
    return project


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str):
    p = _projects.get(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.delete("/{project_id}")
def delete_project(project_id: str):
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    _projects.pop(project_id)
    return {"deleted": project_id}
