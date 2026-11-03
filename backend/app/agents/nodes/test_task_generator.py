from app.agents.nodes.task_generator_node import TaskGeneratorNode
from app.agents.state import AgentState


def main():
    node = TaskGeneratorNode()

    # 🔹 Simulated state (must match what node expects)
    state: AgentState = {
        "user_id": "1",

        "project": {
            "name": "AI Task Manager",
            "description": "A web app where users create and manage tasks with AI suggestions"
        },

        "known_stack": ["HTML", "CSS"],
        "unknown_stack": ["React", "FastAPI"],

        "prerequisites": [],
        "current_concept_index": 0,

        # 🔥 Important for skipping mastered concepts
        "quiz_results": [
            {"concept": "REST APIs", "score": 5, "passed": True, "questions": []},
            {"concept": "React basics", "score": 2, "passed": False, "questions": []},
        ],

        # 🔥 Roadmap (minimal version for testing)
        "roadmap": {
            "total_weeks": 1,
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2025-06-01",
                    "end_date": "2025-06-07",
                    "theme": "React State Management",
                    "goal": "Build a dynamic task list using useState",
                    "topics": [
                        "JSX syntax",
                        "useState hook",
                        "Rendering lists with map()",
                        "Handling user input"
                    ],
                    "deliverable": "React TaskList component with add/remove functionality",
                    "focus_areas": ["React state management"],
                    "difficulty": "easy"
                }
            ],
            "milestones": []
        },

        "current_week": 1,

        # 🔥 For difficulty adjustment
        "weekly_score": None,  # first week

        # placeholders
        "student_approach": None,
        "analysis": None,
        "weekly_tasks": None,
        "completion_status": None,
        "task_quiz_results": None,
        "start_date": "2025-06-01",
        "end_date": "2025-07-01",
        "blackout_dates": []
    }

    # 🔹 Run node
    state = node.run(state)

    tasks = state["weekly_tasks"]

    print("\n=== WEEKLY TASKS GENERATED ===\n")

    for task in tasks:
        print(f"Day {task['day']}: {task['title']}")
        print(f"  Description: {task['description']}")

        print("  Steps:")
        for step in task["steps"]:
            print(f"    → {step}")

        sub = task["submission"]
        print(f"  Submit : {sub['github_folder']}/{sub['filename']}")
        print(f"  Commit : {sub['commit_message']}")
        print(f"  Est.   : {task['estimated_hours']}h")
        print()

    print("✅ Total tasks generated:", len(tasks))


if __name__ == "__main__":
    main()