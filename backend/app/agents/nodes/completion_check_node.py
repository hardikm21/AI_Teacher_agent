from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from app.agents.state import AgentState
from app.services.llm import get_llm
import os
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class CompletionCheckNode:
    """
    Checks whether the student has completed the current week's tasks by
    inspecting their GitHub repository commits.

    Strategy:
      1. Fetch the last two commits from the student's repo branch.
      2. Get the diff (changed files + folders) between them.
      3. Pass the changed paths + the week's expected deliverable to the LLM.
      4. LLM returns a binary verdict: done / not_done, plus a short reason.

    Why two commits?
      - last-to-last commit  : baseline (what existed before this week's work)
      - last commit          : what the student actually pushed

    This catches students who push everything in one commit at the end, as
    well as those who commit incrementally.

    Output written to state["completion_status"]:
      True  → student pushed meaningful work matching the deliverable
      False → no relevant changes found or work is clearly incomplete

    state["completion_reason"] is also set with a short explanation so the
    evaluator and the frontend can give the student useful feedback.
    """

    GITHUB_API = "https://api.github.com"

    SYSTEM_PROMPT = (
        "Respond ONLY with valid JSON. "
        "No explanation, no markdown fences, no text outside the JSON object."
    )

    COMPLETION_CHECK_PROMPT = """You are a strict but fair code submission reviewer.

=== WEEK DELIVERABLE ===
The student was supposed to complete the following this week:
  Deliverable : {deliverable}
  Week theme  : {theme}
  Topics      : {topics}

=== GITHUB ACTIVITY ===
Repository  : {repo}
Branch      : {branch}

Last commit:
  SHA     : {last_sha}
  Message : {last_message}
  Date    : {last_date}

Previous commit (last-to-last):
  SHA     : {prev_sha}
  Message : {prev_message}
  Date    : {prev_date}

Files and folders changed between previous and last commit:
{changed_files}

=== YOUR TASK ===
Decide whether the student has completed the week's deliverable based ONLY
on the changed files listed above.

Rules for your verdict:
1. DONE    → The changed files are in the expected folders for this week's
             deliverable AND the file names/types match what was asked.
             Minor gaps (missing edge cases, minor styling) are acceptable.
2. NOT DONE → No relevant files were changed, OR the changes are clearly in
             the wrong part of the codebase, OR only config/readme files changed
             with no actual feature code.

Be strict about relevance:
- A React component week where only backend files changed → NOT DONE
- A FastAPI week where only .md files changed             → NOT DONE
- A React week where .jsx files were added/modified       → DONE

Provide a short reason (1–2 sentences) that the student can read to
understand what you found.

STRICT OUTPUT RULES:
- Output ONLY valid JSON
- No text before or after
- No markdown fences

Required format:
{{
  "status": "done" | "not_done",
  "reason": "<1-2 sentence explanation for the student>"
}}
"""

    def __init__(self):
        # 🔥 THIS IS THE ONLY CHANGE THAT MATTERS
        self.llm = get_llm(max_tokens=1024)
        self.github_token = os.getenv("GITHUB_TOKEN")

    # ── GitHub helpers ────────────────────────────────────────────────────────

    def _github_headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _fetch_commits(self, owner: str, repo: str, branch: str) -> list[dict]:
        """Fetch the two most recent commits on the given branch."""
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/commits"
        params = {"sha": branch, "per_page": 2}
        response = requests.get(url, headers=self._github_headers(), params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def _fetch_changed_files(self, owner: str, repo: str, base_sha: str, head_sha: str) -> list[str]:
        """
        Get the list of files changed between base_sha and head_sha using
        the GitHub compare API.
        """
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/compare/{base_sha}...{head_sha}"
        response = requests.get(url, headers=self._github_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        return [f["filename"] for f in data.get("files", [])]

    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """
        Extract owner and repo name from a GitHub URL or 'owner/repo' string.
        Supports:
          - https://github.com/owner/repo
          - https://github.com/owner/repo.git
          - owner/repo
        """
        repo_url = repo_url.rstrip("/").replace(".git", "")
        if "github.com" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
        else:
            parts = repo_url.split("/")

        if len(parts) < 2:
            raise ValueError(f"Cannot parse repo URL: {repo_url}")
        return parts[0], parts[1]

    # ── LLM parse ─────────────────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> dict:
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self, state: AgentState, repo_url: str, branch: str = "main") -> AgentState:
        """
        Check the student's GitHub repo and determine if this week's
        deliverable has been completed.

        Args:
            state    : current AgentState
            repo_url : GitHub repo URL or 'owner/repo' string
            branch   : branch to check (default: "main")

        Requires state keys:
          roadmap, current_week, weekly_tasks

        State keys updated:
          completion_status  <- True (done) or False (not done)
          completion_reason  <- short explanation string for student
        """
        roadmap = state.get("roadmap")
        if not roadmap:
            raise ValueError("CompletionCheckNode: state['roadmap'] is missing.")

        current_week = state.get("current_week", 1)
        week_plan = roadmap["weeks"][current_week - 1]

        owner, repo = self._parse_repo_url(repo_url)

        try:
            # ── Step 1: fetch last two commits ────────────────────────────────
            logger.info(f"CompletionCheckNode: fetching commits from {owner}/{repo}@{branch}")
            commits = self._fetch_commits(owner, repo, branch)

            if len(commits) < 2:
                # Only one commit exists — can't do a diff, treat as not done
                logger.warning("CompletionCheckNode: fewer than 2 commits found.")
                return {
                    **state,
                    "completion_status": False,
                    "completion_reason": (
                        "Your repository has fewer than 2 commits. "
                        "Please push your week's work to GitHub before the check runs."
                    ),
                }

            last_commit = commits[0]
            prev_commit = commits[1]

            last_sha     = last_commit["sha"]
            last_message = last_commit["commit"]["message"].split("\n")[0]   # first line only
            last_date    = last_commit["commit"]["committer"]["date"]

            prev_sha     = prev_commit["sha"]
            prev_message = prev_commit["commit"]["message"].split("\n")[0]
            prev_date    = prev_commit["commit"]["committer"]["date"]

            # ── Step 2: get changed files ─────────────────────────────────────
            logger.info(f"CompletionCheckNode: comparing {prev_sha[:7]}...{last_sha[:7]}")
            changed_files = self._fetch_changed_files(owner, repo, prev_sha, last_sha)

            if not changed_files:
                return {
                    **state,
                    "completion_status": False,
                    "completion_reason": (
                        "No file changes were detected between your last two commits. "
                        "Make sure you have pushed your latest work."
                    ),
                }

            changed_files_str = "\n".join(f"  - {f}" for f in changed_files)

            # ── Step 3: LLM verdict ───────────────────────────────────────────
            prompt = self.COMPLETION_CHECK_PROMPT.format(
                deliverable=week_plan["deliverable"],
                theme=week_plan["theme"],
                topics=", ".join(week_plan["topics"]),
                repo=f"{owner}/{repo}",
                branch=branch,
                last_sha=last_sha[:7],
                last_message=last_message,
                last_date=last_date,
                prev_sha=prev_sha[:7],
                prev_message=prev_message,
                prev_date=prev_date,
                changed_files=changed_files_str,
            )

            logger.info("CompletionCheckNode: invoking LLM for verdict")
            response = self.llm.invoke([
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            result = self._parse_response(response.content)

            status = result.get("status", "not_done") == "done"
            reason = result.get("reason", "")

            logger.info(
                f"CompletionCheckNode: week {current_week} → "
                f"{'DONE' if status else 'NOT DONE'} | {reason}"
            )

            return {
                **state,
                "completion_status": status,
                "completion_reason": reason,
            }

        except requests.HTTPError as e:
            logger.error(f"CompletionCheckNode GitHub API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"CompletionCheckNode JSON error: {e}")
            raise
        except Exception as e:
            logger.error(f"CompletionCheckNode error: {e}")
            raise


# ── router for LangGraph ──────────────────────────────────────────────────────

def completion_router(state: AgentState) -> str:
    """
    LangGraph conditional edge after CompletionCheckNode.

    Returns:
      "task_quiz"   → work is done, proceed to TaskQuizGeneratorNode
      "retry_task"  → work is not done, loop back to student
    """
    if state.get("completion_status"):
        return "task_quiz"
    return "retry_task"


# ── smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    node = CompletionCheckNode()

    # Minimal state — only the fields CompletionCheckNode cares about
    state: AgentState = {
        "user_id": "student_01",
        "project": {"name": "AI Task Manager", "description": "..."},
        "known_stack": ["HTML", "CSS", "basic Python"],
        "unknown_stack": ["React", "FastAPI"],
        "prerequisites": [],
        "current_concept_index": 4,
        "quiz_results": [],
        "student_approach": None,
        "analysis": None,
        "roadmap": {
            "total_weeks": 6,
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2025-06-01",
                    "end_date": "2025-06-07",
                    "theme": "Building stateful React components using useState",
                    "goal": "Student can build a task list with add and delete using useState",
                    "topics": [
                        "JSX syntax and conditional rendering",
                        "useState hook",
                        "Props and callbacks",
                        "Array.map() with key props",
                    ],
                    "deliverable": (
                        "React <TaskList> component with add and delete "
                        "functionality using useState"
                    ),
                    "focus_areas": ["React state management"],
                    "difficulty": "easy",
                }
            ],
            "milestones": [],
        },
        "weekly_tasks": None,
        "current_week": 1,
        "completion_status": None,
        "task_quiz_results": None,
        "weekly_score": None,
        "start_date": "2025-06-01",
        "end_date": "2025-07-27",
        "blackout_dates": [],
    }

    # Replace with a real public repo to test end-to-end
    REPO_URL = os.getenv("TEST_REPO_URL", "owner/repo")
    BRANCH   = os.getenv("TEST_BRANCH", "main")

    result = node.run(state, repo_url=REPO_URL, branch=BRANCH)

    print(f"\nCompletion status : {'DONE' if result['completion_status'] else 'NOT DONE'}")
    print(f"Reason            : {result.get('completion_reason', '')}")
    print(f"Router would go to: {completion_router(result)}")