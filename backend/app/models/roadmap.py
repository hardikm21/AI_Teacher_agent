"""
Roadmap response models — mirror of what RoadmapNode writes into AgentState.
Used by planning routes and anywhere we need a typed shape for the roadmap.
"""
from pydantic import BaseModel
from typing import List


class WeekPlan(BaseModel):
    week_number: int
    start_date:  str
    end_date:    str
    theme:       str
    goal:        str
    topics:      List[str]
    deliverable: str
    difficulty:  str


class Milestone(BaseModel):
    week:        int
    description: str


class Roadmap(BaseModel):
    total_weeks: int
    weeks:       List[WeekPlan]
    milestones:  List[Milestone]
