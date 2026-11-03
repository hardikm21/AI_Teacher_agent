"""
Project catalog models — used by teacher-facing routes.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class ProjectCreate(BaseModel):
    name:        str
    description: str
    tech_stack:  List[str] = []
    difficulty:  Optional[str] = "medium"


class Project(ProjectCreate):
    id:         str      = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    assigned:   int      = 0
