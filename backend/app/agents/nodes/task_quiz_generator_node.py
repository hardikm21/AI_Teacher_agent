from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.utils.parser import extract_json
from app.services.llm import get_llm
import logging

logger = logging.getLogger(__name__)


class TaskQuizGeneratorNode:

    SYSTEM_PROMPT = (
        "Respond ONLY with a valid JSON object. "
        "No explanation, no markdown, no text outside the JSON."
    )

    PROMPT = """You are a software engineering mentor writing a quiz about what a student built this week.

Week {week_number}: {theme}
Deliverable: {deliverable}
Topics: {topics}

What the student built each day:
{tasks_summary}

Write EXACTLY 5 MCQ questions that test whether the student UNDERSTANDS what they built.
Questions must be specific to THIS week's work — not generic theory.

Rules:
- Each question has 4 options labelled A, B, C, D
- Exactly one correct answer
- Reference the actual deliverable or decisions made this week
- All strings must be on a single line (no embedded newlines)
- Return ONLY valid JSON, nothing else

Return this JSON object:
{{
  "week": {week_number},
  "concept": "{theme}",
  "questions": [
    {{
      "type": "mcq",
      "question": "<specific question about what they built>",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A",
      "student_answer": null
    }}
  ],
  "passed": false,
  "score": 0
}}"""

    PASS_THRESHOLD = 3   # 3 out of 5

    def __init__(self):
        self.llm = get_llm(max_tokens=800)

    def _tasks_summary(self, weekly_tasks: list) -> str:
        if not weekly_tasks:
            return "  No task data."
        return "\n".join(
            f"  Day {t['day']}: {t['title']}"
            for t in weekly_tasks
        )

    def run(self, state: AgentState) -> AgentState:
        roadmap = state.get("roadmap")
        if not roadmap:
            raise ValueError("TaskQuizGeneratorNode: roadmap missing.")

        current_week = state.get("current_week", 1)
        w            = roadmap["weeks"][current_week - 1]
        weekly_tasks = state.get("weekly_tasks") or []

        prompt = self.PROMPT.format(
            week_number=current_week,
            theme=w["theme"],
            deliverable=w["deliverable"],
            topics=", ".join(w["topics"]),
            tasks_summary=self._tasks_summary(weekly_tasks),
        )
        logger.info(f"TaskQuizGeneratorNode: generating quiz for week {current_week}")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        quiz = extract_json(response.content)
        quiz.setdefault("week",    current_week)
        quiz.setdefault("concept", w["theme"])
        quiz.setdefault("passed",  False)
        quiz.setdefault("score",   0)

        existing = list(state.get("task_quiz_results") or [])
        existing.append(quiz)
        return {**state, "task_quiz_results": existing}

    def grade_quiz(self, state: AgentState, student_answers: list) -> AgentState:
        results      = list(state.get("task_quiz_results") or [])
        if not results:
            raise ValueError("TaskQuizGeneratorNode.grade_quiz: no quiz to grade.")

        quiz         = dict(results[-1])
        questions    = [dict(q) for q in quiz["questions"]]

        score = 0
        for i, q in enumerate(questions):
            ans = student_answers[i].strip() if i < len(student_answers) else ""
            q["student_answer"] = ans
            if ans.upper().startswith(q["correct_answer"].upper()):
                score += 1

        quiz["questions"] = questions
        quiz["score"]     = score
        quiz["passed"]    = score >= self.PASS_THRESHOLD
        results[-1]       = quiz

        logger.info(
            f"TaskQuizGeneratorNode grade: week={quiz['week']} "
            f"score={score}/5 passed={quiz['passed']}"
        )
        return {**state, "task_quiz_results": results}