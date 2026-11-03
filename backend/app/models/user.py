"""
Pydantic user models — currently used by the teacher/projects routers.
Keep these lightweight; the real source of truth for a live session is
AgentState in app.agents.state.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


class User(BaseModel):
    id:         str
    name:       str
    role:       Literal["student", "teacher"] = "student"
    email:      Optional[str] = None
    created_at: datetime      = Field(default_factory=datetime.utcnow)


class StudentProfile(BaseModel):
    user_id:       str
    known_stack:   List[str] = []
    unknown_stack: List[str] = []
    active_session: Optional[str] = None
