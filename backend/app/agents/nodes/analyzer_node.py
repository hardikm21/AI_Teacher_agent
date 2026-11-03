from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.utils.parser import extract_json
from app.services.llm import get_llm
import logging

logger = logging.getLogger(__name__)


class AnalyzerNode:

    SYSTEM_PROMPT = (
        "Respond ONLY with a valid JSON object. "
        "No explanation, no markdown, no text outside the JSON."
    )

    PROMPT = """You are an expert software engineering mentor evaluating a student's project plan.

Project : {project_name} — {project_description}
Knows   : {known_stack}
Learning: {unknown_stack}

Quiz performance:
{quiz_summary}

Student's plan:
{student_approach}

Identify:
- 2-4 positives (what the student understands well)
- 2-4 gaps (weak or missing parts, each with a concrete suggestion)
- overall_understanding: "strong" | "moderate" | "weak"
- 2-4 recommended_focus_areas (specific topics the roadmap must cover)

Rules:
- Be specific — reference the student's actual words
- All strings must be on a single line (no embedded newlines)
- Return ONLY valid JSON, nothing else

Return this JSON object:
{{
  "positives": [
    {{"point": "<strength>", "detail": "<why good>"}}
  ],
  "gaps": [
    {{"point": "<weak area>", "detail": "<what is wrong>", "suggestion": "<concrete fix>"}}
  ],
  "overall_understanding": "moderate",
  "recommended_focus_areas": ["<specific topic>"]
}}"""

    def __init__(self):
        self.llm = get_llm(max_tokens=700)

    def _quiz_summary(self, state: AgentState) -> str:
        results = state.get("quiz_results", [])
        if not results:
            return "No quiz data."
        return "\n".join(
            f"  {r['concept']}: {r['score']}/5 [{'PASS' if r['passed'] else 'FAIL'}]"
            for r in results
        )

    def run(self, state: AgentState) -> AgentState:
        approach = state.get("student_approach", "")
        if not approach:
            raise ValueError("AnalyzerNode: student_approach is empty.")

        p = state["project"]
        prompt = self.PROMPT.format(
            project_name=p.get("name", ""),
            project_description=p.get("description", ""),
            known_stack=", ".join(state["known_stack"]),
            unknown_stack=", ".join(state["unknown_stack"]),
            quiz_summary=self._quiz_summary(state),
            student_approach=approach,
        )
        logger.info("AnalyzerNode: invoking LLM")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        analysis = extract_json(response.content)
        logger.info(
            f"AnalyzerNode: understanding={analysis.get('overall_understanding')} "
            f"gaps={len(analysis.get('gaps', []))} positives={len(analysis.get('positives', []))}"
        )
        return {**state, "analysis": analysis}