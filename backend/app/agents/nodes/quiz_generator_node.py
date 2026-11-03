from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.utils.parser import extract_json
from app.services.llm import get_llm
import logging

logger = logging.getLogger(__name__)


class QuizGeneratorNode:

    SYSTEM_PROMPT = (
        "Respond ONLY with a valid JSON object. "
        "No explanation, no markdown, no text outside the JSON."
    )

    PROMPT = """You are a software engineering teacher writing a short quiz.

Concept    : {concept}
Explanation: {explanation}
Toy task   : {toy_task}
Student knows: {known_stack}

Write EXACTLY 5 MCQ questions to test understanding of this concept.

Rules:
- Each question has 4 options labelled A, B, C, D
- Exactly one correct answer per question
- Distractors must be plausible but clearly wrong to someone who studied the concept
- Do NOT make trick questions
- All strings must be on a single line (no newlines inside strings)

Return ONLY this JSON object:
{{
  "concept": "{concept}",
  "questions": [
    {{
      "type": "mcq",
      "question": "<question text>",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A",
      "student_answer": null
    }}
  ],
  "passed": false,
  "score": 0
}}"""

    PASS_THRESHOLD = 0   # 3 out of 5 to pass

    def __init__(self):
        self.llm = get_llm(max_tokens=800)

    def run(self, state: AgentState) -> AgentState:
        index   = state["current_concept_index"]
        prereqs = state["prerequisites"]
        if index >= len(prereqs):
            logger.warning("QuizGeneratorNode: no more concepts.")
            return state

        c = prereqs[index]
        prompt = self.PROMPT.format(
            concept=c["concept"],
            explanation=c["explanation"],
            toy_task=c["toy_task"],
            known_stack=", ".join(state["known_stack"]),
        )
        logger.info(f"QuizGeneratorNode: generating quiz for concept {index + 1}/{len(prereqs)}: '{c['concept']}'")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        quiz = extract_json(response.content)
        quiz.setdefault("concept", c["concept"])
        quiz.setdefault("passed",  False)
        quiz.setdefault("score",   0)

        return {**state, "quiz_results": list(state["quiz_results"]) + [quiz]}

    def grade_quiz(self, state: AgentState, student_answers: list) -> AgentState:
        quiz_results = list(state["quiz_results"])
        quiz         = dict(quiz_results[-1])
        questions    = [dict(q) for q in quiz["questions"]]

        score = 0
        for i, q in enumerate(questions):
            ans = student_answers[i].strip() if i < len(student_answers) else ""
            q["student_answer"] = ans
            # compare first character only (student may type "A" or "A. text")
            if ans.upper().startswith(q["correct_answer"].upper()):
                score += 1

        passed          = score >= self.PASS_THRESHOLD
        quiz["questions"] = questions
        quiz["score"]     = score
        quiz["passed"]    = passed
        quiz_results[-1]  = quiz

        new_index = state["current_concept_index"] + (1 if passed else 0)
        logger.info(
            f"QuizGeneratorNode grade: '{quiz['concept']}' "
            f"score={score}/5 passed={passed} next_index={new_index}"
        )
        return {
            **state,
            "quiz_results":          quiz_results,
            "current_concept_index": new_index,
        }


def prereq_loop_router(state: AgentState) -> str:
    idx   = state["current_concept_index"]
    total = len(state["prerequisites"])
    return "quiz_concept" if idx < total else "exit_prereq"