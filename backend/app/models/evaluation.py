"""
Evaluator models — shape of what EvaluatorNode writes into state.
"""
from pydantic import BaseModel
from typing import Optional


class EvaluationBreakdown(BaseModel):
    completion_points:     int
    quiz_points:           int
    reflection_points:     int
    difficulty_adjustment: int


class EvaluationFeedback(BaseModel):
    strength:      str
    improvement:   str
    message:       str
    next_week_tip: str


class Evaluation(BaseModel):
    week_number:      int
    score:            float
    score_display:    float
    breakdown:        Optional[EvaluationBreakdown] = None
    feedback:         EvaluationFeedback
    project_complete: bool
    next_week:        Optional[int] = None
