from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.utils.parser import extract_json
from app.services.llm import get_llm
import logging

logger = logging.getLogger(__name__)


class EvaluatorNode:

    SYSTEM_PROMPT = (
        "Respond ONLY with a valid JSON object. "
        "No explanation, no markdown, no text outside the JSON."
    )

    PROMPT = """You are a software engineering mentor evaluating a student's weekly performance.

Project : {project_name}
Week    : {week_number} of {total_weeks}
Theme   : {theme}
Deliverable: {deliverable}
Difficulty : {difficulty}

Completion: {completion_status}
Reason    : {completion_reason}

Quiz score: {quiz_score}/5 (passed: {quiz_passed})
Question results:
{quiz_breakdown}

Scoring rubric (-5 to +5):
+5: deliverable done + 5/5 quiz
+4: done + 4/5
+3: done + 3/5
+2: done + 2/5
+1: done + 1/5
 0: done + 0/5
-2: not done + 3-5/5 (understands but didn't submit)
-3: not done + 1-2/5
-5: not done + 0/5
Adjust +1 if difficulty=hard and score>=2.
Adjust -1 if difficulty=easy and score<2.
Clamp final to [-5, +5].

Provide specific feedback referencing the actual quiz results.
All strings must be on a single line (no embedded newlines).
Return ONLY valid JSON, nothing else.

Return this JSON object:
{{
  "score": <int -5 to +5>,
  "breakdown": {{
    "completion_points": <int>,
    "quiz_points": <int>,
    "difficulty_adjustment": <int>
  }},
  "feedback": {{
    "strength": "<specific thing done well>",
    "improvement": "<specific actionable improvement>",
    "message": "<one honest motivating sentence>",
    "next_week_tip": "<one concrete action for next week>"
  }}
}}"""

    def __init__(self):
        self.llm = get_llm(max_tokens=500)

    @staticmethod
    def _map_score(score: float) -> float:
        return round(score + 5, 1)

    def _quiz_breakdown(self, task_quiz_results: list) -> str:
        if not task_quiz_results:
            return "  No data."
        latest = task_quiz_results[-1]
        lines  = []
        for i, q in enumerate(latest.get("questions", []), 1):
            correct = q.get("correct_answer", "")
            student = q.get("student_answer", "") or ""
            ok      = student.upper().startswith(correct.upper())
            lines.append(f"  Q{i}: {'✓' if ok else '✗'} (expected {correct}, got {student or 'no answer'})")
        return "\n".join(lines) if lines else "  No graded questions."

    def run(self, state: AgentState) -> AgentState:
        roadmap = state.get("roadmap")
        if not roadmap:
            raise ValueError("EvaluatorNode: roadmap missing.")

        current_week      = state.get("current_week", 1)
        total_weeks       = roadmap.get("total_weeks", len(roadmap["weeks"]))
        w                 = roadmap["weeks"][current_week - 1]
        task_quiz_results = state.get("task_quiz_results") or []
        latest_quiz       = task_quiz_results[-1] if task_quiz_results else {}

        prompt = self.PROMPT.format(
            project_name=state["project"].get("name", ""),
            week_number=current_week,
            total_weeks=total_weeks,
            theme=w["theme"],
            deliverable=w["deliverable"],
            difficulty=w.get("difficulty", "medium"),
            completion_status="YES" if state.get("completion_status") else "NO",
            completion_reason=state.get("completion_reason", "N/A"),
            quiz_score=latest_quiz.get("score", 0),
            quiz_passed=latest_quiz.get("passed", False),
            quiz_breakdown=self._quiz_breakdown(task_quiz_results),
        )
        logger.info(f"EvaluatorNode: evaluating week {current_week}")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        result        = extract_json(response.content)
        raw_score     = max(-5, min(5, int(result.get("score", 0))))
        display_score = self._map_score(raw_score)
        is_final      = current_week >= total_weeks

        logger.info(f"EvaluatorNode: score={raw_score} ({display_score}/10) final={is_final}")
        return {
            **state,
            "weekly_score":         raw_score,
            "weekly_score_display": display_score,
            "evaluation_feedback":  result.get("feedback", {}),
            "evaluation_breakdown": result.get("breakdown", {}),
            "current_week":         current_week if is_final else current_week + 1,
            "project_complete":     is_final,
        }


def weekly_loop_router(state: AgentState) -> str:
    return "project_complete" if state.get("project_complete") else "next_week"