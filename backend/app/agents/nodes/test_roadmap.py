from app.agents.nodes.roadmap_node import RoadmapNode
from app.agents.state import AgentState


def main():
    node = RoadmapNode()

    # 🔹 Simulated state (must match what RoadmapNode expects)
    state: AgentState = {
        "user_id": "1",

        "project": {
            "name": "AI Task Manager",
            "description": "A web app where users manage tasks with AI suggestions"
        },

        "known_stack": ["HTML", "CSS"],
        "unknown_stack": ["React", "FastAPI"],

        "prerequisites": [],
        "current_concept_index": 0,

        "quiz_results": [
            {"concept": "React basics", "score": 2, "passed": False, "questions": []},
            {"concept": "FastAPI", "score": 4, "passed": True, "questions": []}
        ],

        "student_approach": "I will build a React frontend and FastAPI backend",

        # 🔥 IMPORTANT: This comes from AnalyzerNode
        "analysis": {
            "positives": [
                {
                    "point": "Understands backend basics",
                    "detail": "Student correctly identified use of APIs"
                }
            ],
            "gaps": [
                {
                    "point": "No state management plan",
                    "detail": "Student did not explain how React state will be handled",
                    "suggestion": "Add a week focused on useState and useEffect"
                },
                {
                    "point": "Weak frontend-backend connection",
                    "detail": "Student vaguely mentioned API calls",
                    "suggestion": "Practice fetch/axios integration"
                }
            ],
            "overall_understanding": "moderate",
            "recommended_focus_areas": [
                "React state management",
                "API integration"
            ]
        },

        # timeline
        "start_date": "2025-06-01",
        "end_date": "2025-07-15",
        "blackout_dates": ["2025-06-20"],

        # placeholders
        "roadmap": None,
        "weekly_tasks": None,
        "current_week": 0,
        "completion_status": None,
        "task_quiz_results": None,
        "weekly_score": None,
    }

    # 🔹 Run roadmap node
    state = node.run(state)

    roadmap = state["roadmap"]

    print("\n=== ROADMAP ===\n")

    print(f"Total Weeks: {roadmap['total_weeks']}\n")

    for week in roadmap["weeks"]:
        print(f"Week {week['week_number']}")
        print(f"  Dates      : {week['start_date']} → {week['end_date']}")
        print(f"  Theme      : {week['theme']}")
        print(f"  Goal       : {week['goal']}")
        print(f"  Topics     : {', '.join(week['topics'])}")
        print(f"  Deliverable: {week['deliverable']}")

        if week.get("focus_areas"):
            print(f"  Focus      : {', '.join(week['focus_areas'])}")

        print()

    print("=== MILESTONES ===")
    for m in roadmap["milestones"]:
        print(f"Week {m['week']}: {m['description']}")


if __name__ == "__main__":
    main()