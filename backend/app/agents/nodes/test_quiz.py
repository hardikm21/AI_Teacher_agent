from app.agents.nodes.quiz_generator_node import QuizGeneratorNode
from app.agents.state import AgentState


def main():
    node = QuizGeneratorNode()

    # 👇 Simulate output from prerequisite node
    state: AgentState = {
        "user_id": "1",
        "project": {
            "name": "AI Task Manager",
            "description": "A web app to manage tasks with AI suggestions"
        },
        "known_stack": ["HTML", "CSS"],
        "unknown_stack": ["React", "FastAPI"],

        "prerequisites": [
            {
                "concept": "React Components",
                "explanation": "Components are reusable UI blocks in React.",
                "toy_task": "Build a simple task list component",
                "estimated_time": "1 day"
            }
        ],

        "current_concept_index": 0,
        "quiz_results": [],

        # placeholders
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

    # 🔹 Step 1: Generate quiz
    state = node.run(state)

    quiz = state["quiz_results"][-1]

    print("\n=== QUIZ GENERATED ===\n")
    print(f"Concept: {quiz['concept']}\n")

    for i, q in enumerate(quiz["questions"], 1):
        print(f"Q{i} [{q['type'].upper()}]: {q['question']}")

        if q["options"]:
            for opt in q["options"]:
                print(f"   {opt}")

        print()

    # 🔹 Step 2: Simulate answers (all correct)
    answers = [q["correct_answer"] for q in quiz["questions"]]

    state = node.grade_quiz(state, answers)

    result = state["quiz_results"][-1]

    print("=== RESULT ===")
    print(f"Score  : {result['score']}/5")
    print(f"Passed : {result['passed']}")
    print(f"Next concept index: {state['current_concept_index']}")


if __name__ == "__main__":
    main()