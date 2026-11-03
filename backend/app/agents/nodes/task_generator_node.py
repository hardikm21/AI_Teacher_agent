from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.utils.parser import extract_json
from app.services.llm import get_llm
import logging

logger = logging.getLogger(__name__)


class TaskGeneratorNode:

    SYSTEM_PROMPT = (
        "Respond ONLY with a valid JSON array. "
        "No explanation, no markdown, no text outside the array."
    )

    PROMPT = """You are a software engineering mentor generating weekly tasks.

Project : {project_name} — {project_description}
Knows   : {known_stack}

Week {week_number}: {theme}
Goal       : {goal}
Topics     : {topics}
Deliverable: {deliverable}
Difficulty : {difficulty}
Prev score : {previous_score} (scale -5 to +5; below 0 means slow down)
Already mastered (do not re-teach): {mastered}

Generate EXACTLY 5 daily tasks (Mon–Fri):
- Day 1: project setup + foundation for this week's theme
- Day 5: complete and push the deliverable to GitHub

Each task must have:
- specific title
- 2-3 sentence description (what and why)
- 3-5 concrete executable steps
- exact github_folder and filename for submission
- conventional commit message (feat/fix/chore prefix)
- estimated_hours (1-4 based on difficulty)

Rules:
- All strings on a single line (no embedded newlines)
- Return ONLY the JSON array, nothing else

Return this JSON array:
[
  {{
    "day": 1,
    "title": "<specific task title>",
    "description": "<2-3 sentences>",
    "steps": ["<step 1>", "<step 2>", "<step 3>"],
    "submission": {{
      "github_folder": "<repo subfolder>",
      "filename": "<filename>",
      "commit_message": "<conventional commit>"
    }},
    "estimated_hours": 2
  }}
]"""

    def __init__(self):
        self.llm = get_llm(max_tokens=1400)

    def run(self, state: AgentState) -> AgentState:
        roadmap = state.get("roadmap")
        if not roadmap:
            raise ValueError("TaskGeneratorNode: roadmap missing.")

        current_week = state.get("current_week", 1)
        weeks        = roadmap.get("weeks", [])
        if current_week > len(weeks):
            logger.warning("TaskGeneratorNode: current_week exceeds roadmap.")
            return state

        w      = weeks[current_week - 1]
        p      = state["project"]
        passed = [r["concept"] for r in state.get("quiz_results", []) if r.get("passed")]
        prev   = state.get("weekly_score")

        prompt = self.PROMPT.format(
            project_name=p.get("name", ""),
            project_description=p.get("description", ""),
            known_stack=", ".join(state["known_stack"]),
            week_number=w["week_number"],
            theme=w["theme"],
            goal=w["goal"],
            topics=", ".join(w["topics"]),
            deliverable=w["deliverable"],
            difficulty=w.get("difficulty", "medium"),
            previous_score=str(prev) if prev is not None else "N/A (first week)",
            mastered=", ".join(passed) if passed else "None",
        )
        logger.info(f"TaskGeneratorNode: generating tasks for week {current_week}")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        logger.debug(f"RAW TASK OUTPUT:\n{response.content[:1000]}")

        tasks = extract_json(response.content)

        # 🔥 Normalize output
        if isinstance(tasks, dict):
            if "tasks" in tasks:
                tasks = tasks["tasks"]
            elif "data" in tasks:
                tasks = tasks["data"]
            else:
                tasks = [tasks]

        if not isinstance(tasks, list):
            raise ValueError("TaskGeneratorNode: expected JSON array")

        if len(tasks) != 5:
            logger.warning(f"Expected 5 tasks, got {len(tasks)}")

        logger.info(f"TaskGeneratorNode: {len(tasks)} tasks generated")
        return {**state, "weekly_tasks": tasks}