from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from app.agents.state import AgentState, Prerequisite
from app.services.llm import get_llm
import os
import json
import logging

logger = logging.getLogger(__name__)


class PrerequisiteNode:
    """
    Generates a structured list of prerequisite concepts the student must learn
    before starting the project.

    Each concept gets:
      - concept        : name of the topic
      - explanation    : short, plain-English description of what it is
      - toy_task       : a small, one-day project that proves understanding
      - estimated_time : always "1 day"

    Concepts are ordered so each one builds on the previous.

    Runs ONCE.  The per-concept quiz loop is handled downstream by
    QuizGeneratorNode, which uses state["current_concept_index"] to walk
    through this list one concept at a time.
    """

    SYSTEM_PROMPT = (
        "Respond ONLY with valid JSON. "
        "No explanation, no markdown fences, no text outside the JSON array."
    )

    PREREQUISITE_PROMPT = """You are an expert software engineering teacher designing a personalised, project-driven learning path.

    A student wants to build the following project:
    Project name       : {project_name}
    Project description: {project_description}

    The student ALREADY knows : {known_stack}
    The student does NOT know  : {unknown_stack}

    Your job:
    1. Identify ONLY the essential concepts from the unknown stack required to build THIS project.
    2. Order the concepts from beginner → advanced so each builds on the previous.
    3. Keep the list focused (5–8 concepts maximum).

    For EACH concept, you MUST include:

    - concept:
    Clear topic name (e.g., "React State", "REST API Design")

    - why_needed:
    Explain specifically WHY this concept is needed for THIS project (not generic)

    - explanation:
    2–4 sentences explaining the concept in simple terms (assume beginner level but not absolute beginner)

    - toy_task:
    A ONE-DAY mini project that is:
        • directly related to the main project
        • practical and hands-on
        • NOT generic (avoid unrelated examples like weather apps or book systems)
        • builds intuition for the actual project

    - estimated_time:
    Always "1 day"

    STRICT QUALITY RULES:
    - Concepts must be directly useful for the given project
    - Avoid generic explanations like "JavaScript is a programming language"
    - Avoid unrelated toy tasks (everything must connect to the project)
    - Ensure logical order (no concept depends on a later one)
    - Keep explanations concise and clear

    STRICT OUTPUT RULES:
    - Output ONLY a valid JSON array
    - No explanation outside JSON
    - No markdown fences
    - No extra text
    - Every string must be on ONE LINE (no line breaks inside values)

    Required format:
    [
    {{
        "concept": "",
        "why_needed": "",
        "explanation": "",
        "toy_task": "",
        "estimated_time": "1 day"
    }}
    ]
    """

    def __init__(self):
        # 🔥 THIS IS THE ONLY CHANGE THAT MATTERS
        self.llm = get_llm(max_tokens=1024)

    def _parse_response(self, raw: str) -> list:
        """Strip markdown fences if the model adds them despite instructions."""
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)

    def run(self, state: AgentState) -> AgentState:
        """
        Calls the LLM, parses the concept list, and writes it into state.

        State keys updated:
          prerequisites          <- list[Prerequisite]
          current_concept_index  <- 0  (reset for the loop)
          quiz_results           <- []  (no quizzes taken yet)
        """
        project = state["project"]
        known_stack = ", ".join(state["known_stack"])
        unknown_stack = ", ".join(state["unknown_stack"])

        prompt = self.PREREQUISITE_PROMPT.format(
            project_name=project.get("name", ""),
            project_description=project.get("description", ""),
            known_stack=known_stack,
            unknown_stack=unknown_stack,
        )

        try:
            logger.info("PrerequisiteNode: invoking LLM")
            response = self.llm.invoke([
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            prerequisites: list[Prerequisite] = self._parse_response(response.content)
            logger.info(f"PrerequisiteNode: {len(prerequisites)} concepts generated")

            return {
                **state,
                "prerequisites": prerequisites,
                "current_concept_index": 0,
                "quiz_results": [],
            }

        except json.JSONDecodeError as e:
            logger.error(f"PrerequisiteNode JSON error: {e}")
            raise
        except Exception as e:
            logger.error(f"PrerequisiteNode error: {e}")
            raise


# ── smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    node = PrerequisiteNode()

    state: AgentState = {
        "user_id": "student_01",
        "project": {
            "name": "AI Task Manager",
            "description": (
                "A web app where users create, assign, and track tasks "
                "with an AI assistant that suggests priorities."
            ),
        },
        "known_stack": ["HTML", "CSS", "basic Python"],
        "unknown_stack": ["React", "FastAPI", "REST APIs", "React hooks"],
        "prerequisites": [],
        "current_concept_index": 0,
        "quiz_results": [],
        "student_approach": None,
        "analysis": None,
        "roadmap": None,
        "weekly_tasks": None,
        "current_week": 0,
        "completion_status": None,
        "task_quiz_results": None,
        "weekly_score": None,
        "start_date": None,
        "end_date": None,
        "blackout_dates": None,
    }

    result = node.run(state)
    print(f"\nGenerated {len(result['prerequisites'])} concepts:\n")
    for i, p in enumerate(result["prerequisites"], 1):
        print(f"{i}. {p['concept']}  ({p['estimated_time']})")
        print(f"   Explanation : {p['explanation']}")
        print(f"   Toy task    : {p['toy_task']}\n")