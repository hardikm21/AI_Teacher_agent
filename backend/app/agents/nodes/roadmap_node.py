from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.utils.parser import extract_json
from app.services.llm import get_llm
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class RoadmapNode:
    """
    Builds a week-by-week project roadmap personalised to the student.
    Uses the analyzer output (gaps, focus areas, understanding level) to
    weight the weekly plan.
    """

    SYSTEM_PROMPT = (
        "You are an expert software engineering mentor. "
        "Respond ONLY with valid JSON. "
        "No explanation, no markdown fences, no text before or after the JSON."
    )

    # Kept shorter to avoid Groq token-limit truncation
    ROADMAP_PROMPT = """Create a personalised project roadmap and return JSON.

PROJECT: {project_name} — {project_description}

STUDENT
Known: {known_stack}
Learning: {unknown_stack}
Understanding level: {overall_understanding}

GAPS (address these first, in order):
{gaps_summary}

FOCUS AREAS (every item must appear in at least one week):
{focus_areas}

QUIZ FAILURES (reinforce in week 1 or 2):
{quiz_summary}

TIMELINE
Start: {start_date}  End: {end_date}  Available weeks: {available_weeks}
Blackout dates (no tasks): {blackout_dates}

RULES
1. Week 1 addresses the biggest gap/failure — never starts with easy known material
2. Pace: weak=slow ramp, moderate=standard, strong=fast integration
3. Every week needs: theme, goal, 2-4 specific topics, working deliverable, difficulty
4. Deliverable must be a GitHub-pushable feature (not "read docs")
5. Difficulty arc: easy → medium → hard → medium (polish week)
6. Final week = polish, testing, README
7. 2-4 milestones at real turning points
8. Output ONLY valid JSON, all strings single-line (no embedded newlines)

REQUIRED FORMAT
{{
  "total_weeks": <int>,
  "weeks": [
    {{
      "week_number": 1,
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "theme": "<specific focus>",
      "goal": "<measurable outcome>",
      "topics": ["<specific topic>", "<specific topic>"],
      "deliverable": "<working GitHub feature>",
      "focus_areas": ["<focus area or empty list>"],
      "difficulty": "easy"
    }}
  ],
  "milestones": [
    {{"week": <int>, "description": "<meaningful checkpoint>"}}
  ]
}}"""

    def __init__(self):
        self.llm = get_llm(max_tokens=3000)

    def _format_gaps(self, analysis: dict) -> str:
        lines = []
        for i, g in enumerate(analysis.get("gaps", []), 1):
            lines.append(f"  {i}. {g['point']}: {g['detail']} → Fix: {g['suggestion']}")
        return "\n".join(lines) if lines else "  None."

    def _build_quiz_summary(self, state: AgentState) -> str:
        results = state.get("quiz_results", [])
        failed  = [r for r in results if not r["passed"]]
        if not failed:
            return "  All passed."
        return "\n".join(f"  FAILED: {r['concept']} ({r['score']}/5)" for r in failed)

    def _compute_available_weeks(self, start_date, end_date, blackout_dates) -> int:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end   = datetime.strptime(end_date,   "%Y-%m-%d")
            raw   = max(1, (end - start).days // 7)
            return max(1, raw - len(blackout_dates) // 7)
        except Exception:
            return 4

    def run(self, state: AgentState) -> AgentState:
        analysis = state.get("analysis")
        if not analysis:
            raise ValueError("RoadmapNode: analysis is missing. Run AnalyzerNode first.")

        project      = state["project"]
        start_date   = state.get("start_date") or datetime.today().strftime("%Y-%m-%d")
        end_date     = state.get("end_date")   or (datetime.today() + timedelta(weeks=8)).strftime("%Y-%m-%d")
        blackout     = state.get("blackout_dates") or []
        avail_weeks  = self._compute_available_weeks(start_date, end_date, blackout)

        prompt = self.ROADMAP_PROMPT.format(
            project_name=project.get("name", ""),
            project_description=project.get("description", ""),
            known_stack=", ".join(state["known_stack"]),
            unknown_stack=", ".join(state["unknown_stack"]),
            overall_understanding=analysis.get("overall_understanding", "moderate"),
            gaps_summary=self._format_gaps(analysis),
            focus_areas=", ".join(analysis.get("recommended_focus_areas", [])),
            quiz_summary=self._build_quiz_summary(state),
            start_date=start_date,
            end_date=end_date,
            available_weeks=avail_weeks,
            blackout_dates=", ".join(blackout) if blackout else "None",
        )

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"RoadmapNode: invoking LLM (attempt {attempt})")
                response = self.llm.invoke([
                    SystemMessage(content=self.SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ])
                raw = response.content.strip()
                logger.debug(f"RoadmapNode raw response (first 300): {raw[:300]}")

                roadmap = extract_json(raw)

                # Validate
                if "weeks" not in roadmap or not roadmap["weeks"]:
                    raise ValueError("Roadmap has no 'weeks' array")
                if "total_weeks" not in roadmap:
                    roadmap["total_weeks"] = len(roadmap["weeks"])
                if "milestones" not in roadmap:
                    roadmap["milestones"] = []

                logger.info(
                    f"RoadmapNode: {roadmap['total_weeks']} weeks | "
                    f"{len(roadmap['milestones'])} milestones"
                )
                return {**state, "roadmap": roadmap, "current_week": 1}

            except Exception as e:
                last_error = e
                logger.warning(f"RoadmapNode attempt {attempt} failed: {e}")

        logger.error(f"RoadmapNode: all attempts failed. Last error: {last_error}")
        raise ValueError(f"RoadmapNode failed after {MAX_RETRIES} attempts: {last_error}")


# ── smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    node = RoadmapNode()
    state = {
        "user_id": "test",
        "project": {"name": "AI Task Manager", "description": "Task management with AI priorities."},
        "known_stack": ["HTML", "CSS", "basic Python"],
        "unknown_stack": ["React", "FastAPI"],
        "prerequisites": [],
        "current_concept_index": 2,
        "quiz_results": [
            {"concept": "REST APIs", "score": 5, "passed": True,  "questions": []},
            {"concept": "React",     "score": 2, "passed": False, "questions": []},
        ],
        "student_approach": "I'll build React frontend and FastAPI backend.",
        "analysis": {
            "positives": [{"point": "Knows FastAPI routing", "detail": "Described endpoints correctly."}],
            "gaps": [
                {"point": "No state management plan", "detail": "Didn't mention useState/useEffect.", "suggestion": "Dedicate week 2 to useState."},
                {"point": "Vague AI integration", "detail": "Said 'add AI button' with no plan.", "suggestion": "Plan a POST call to HuggingFace inference API."},
            ],
            "overall_understanding": "moderate",
            "recommended_focus_areas": ["React state management", "Frontend-backend integration"],
        },
        "roadmap": None, "weekly_tasks": None, "current_week": 0,
        "completion_status": None, "completion_reason": None,
        "task_quiz_results": None, "weekly_score": None, "weekly_score_display": None,
        "evaluation_feedback": None, "project_complete": False,
        "start_date": "2025-06-01", "end_date": "2025-07-27", "blackout_dates": [],
        "repo_url": None, "github_branch": "main",
    }
    result = node.run(state)
    import json
    roadmap = result["roadmap"]
    print(f"\nTotal weeks: {roadmap['total_weeks']}\n")
    for w in roadmap["weeks"]:
        print(f"Week {w['week_number']} [{w['difficulty']}]: {w['theme']}")
        print(f"  Deliverable: {w['deliverable']}\n")