"""
Weekly-task models — match the TaskGeneratorNode output shape.
"""
from pydantic import BaseModel
from typing import List


class TaskSubmission(BaseModel):
    github_folder:  str
    filename:       str
    commit_message: str


class DailyTask(BaseModel):
    day:             int
    title:           str
    description:     str
    steps:           List[str]
    submission:      TaskSubmission
    estimated_hours: int
