import logging
from app.agents.nodes.task_quiz_generator_node import TaskQuizGeneratorNode
from app.agents.state import AgentState

logging.basicConfig(level=logging.INFO)


def main():
    node = TaskQuizGeneratorNode()

    # ✅ Minimal state required for TaskQuizGeneratorNode
    state: AgentState = {
        "user_id": "student_01",

        "project": {
            "name": "AI Task Manager",
            "description": "A web app for task management with AI suggestions"
        },

        "known_stack": ["HTML", "CSS", "basic Python"],
        "unknown_stack": ["React", "FastAPI"],

        "prerequisites": [],
        "current_concept_index": 0,
        "quiz_results": [],

        "student_approach": None,
        "analysis": None,

        # ✅ REQUIRED: roadmap
        "roadmap": {
            "total_weeks": 1,
            "weeks": [
                {
                    "week_number": 1,
                    "theme": "React State Management",
                    "goal": "Build a task list using useState",
                    "topics": ["useState", "JSX", "props", "map"],
                    "deliverable": "TaskList component with add/remove tasks",
                    "difficulty": "easy"
                }
            ]
        },

        # ✅ REQUIRED: tasks from TaskGeneratorNode
        "weekly_tasks": [
            {
                "day": 1,
                "title": "Setup React project",
                "description": "Initialize React app and folder structure"
            },
            {
                "day": 2,
                "title": "Implement useState",
                "description": "Create state for tasks"
            },
            {
                "day": 3,
                "title": "Render task list",
                "description": "Use map() to render tasks"
            },
            {
                "day": 4,
                "title": "Add delete functionality",
                "description": "Remove tasks from list"
            },
            {
                "day": 5,
                "title": "Finalize component",
                "description": "Complete and clean code"
            }
        ],

        "current_week": 1,
        "task_quiz_results": [],

        "completion_status": None,
        "task_quiz_results": [],
        "weekly_score": None,

        "start_date": None,
        "end_date": None,
        "blackout_dates": None,
    }

    # ── Step 1: Generate quiz ─────────────────────────────
    state = node.run(state)

    quiz = state["task_quiz_results"][-1]

    print("\n=== TASK QUIZ GENERATED ===\n")
    print(f"Concept: {quiz.get('concept', '')}\n")

    for i, q in enumerate(quiz["questions"], 1):
        print(f"Q{i} [{q['type'].upper()}]: {q['question']}")
        if q.get("options"):
            for opt in q["options"]:
                print(f"   {opt}")
        print()

    # ── Step 2: Simulate answers (all correct) ────────────
    answers = []
    for q in quiz["questions"]:
        if q["type"] == "mcq":
            answers.append(q["correct_answer"])
        elif q["type"] == "code":
            answers.append(q["correct_answer"])
        else:
            answers.append("Because it manages state properly")  # reflection/text

    state = node.grade_quiz(state, answers)

    result = state["task_quiz_results"][-1]

    print("=== RESULT ===")
    print(f"Score  : {result['score']}/4")
    print(f"Passed : {result['passed']}")

    if result["passed"]:
        print("\nNext step: next_week")
    else:
        print("\nNext step: repeat_week")


if __name__ == "__main__":
    main()