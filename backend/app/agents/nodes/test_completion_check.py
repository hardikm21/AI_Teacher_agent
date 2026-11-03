from app.agents.nodes.completion_check_node import CompletionCheckNode, completion_router
from app.agents.state import AgentState


def main():
    node = CompletionCheckNode()

    # 🔹 Minimal required state
    state: AgentState = {
        "user_id": "1",

        "project": {
            "name": "AI Task Manager",
            "description": "Task manager with React + FastAPI"
        },

        "known_stack": ["HTML", "CSS"],
        "unknown_stack": ["React", "FastAPI"],

        "prerequisites": [],
        "current_concept_index": 0,
        "quiz_results": [],
        "student_approach": None,
        "analysis": None,

        # 🔥 Roadmap (only current week needed)
        "roadmap": {
            "total_weeks": 1,
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2025-06-01",
                    "end_date": "2025-06-07",
                    "theme": "React State Management",
                    "goal": "Build a dynamic task list",
                    "topics": [
                        "useState hook",
                        "JSX rendering",
                        "map() for lists"
                    ],
                    "deliverable": "React TaskList component with add/remove tasks",
                    "focus_areas": ["React"],
                    "difficulty": "easy"
                }
            ],
            "milestones": []
        },

        "current_week": 1,

        # placeholders
        "weekly_tasks": None,
        "completion_status": None,
        "completion_reason": None,
        "task_quiz_results": None,
        "weekly_score": None,
        "start_date": "2025-06-01",
        "end_date": "2025-07-01",
        "blackout_dates": []
    }

    # 🔴 IMPORTANT: Replace with a REAL public repo
    repo_url = "facebook/react"   # or your own repo
    branch = "main"

    # 🔹 Run node
    result = node.run(state, repo_url=repo_url, branch=branch)

    print("\n=== COMPLETION CHECK RESULT ===\n")

    print("Status :", "DONE" if result["completion_status"] else "NOT DONE")
    print("Reason :", result.get("completion_reason", ""))

    # 🔹 Test router
    next_step = completion_router(result)
    print("\nNext step in graph:", next_step)


if __name__ == "__main__":
    main()