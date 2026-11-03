# backend/app/agents/nodes/test.py

from app.agents.nodes.prerequisite_node import PrerequisiteNode
from app.agents.state import AgentState


def main():
    node = PrerequisiteNode()

    state: AgentState = {
        "user_id": "1",
        "project": {
            "name": "AI Task Manager",
            "description": "A web app to manage tasks with AI suggestions"
        },
        "known_stack": ["HTML", "CSS"],
        "unknown_stack": ["React", "FastAPI"],

        "prerequisites": [],
        "current_concept_index": 0,
        "quiz_results": [],

        # placeholders (needed for state)
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

    print("\n=== PREREQUISITES GENERATED ===\n")

    for i, concept in enumerate(result["prerequisites"], 1):
        print(f"{i}. {concept['concept']}")
        print(f"   Explanation : {concept['explanation']}")
        print(f"   Toy Task    : {concept['toy_task']}")
        print(f"   Time        : {concept['estimated_time']}\n")


if __name__ == "__main__":
    main()