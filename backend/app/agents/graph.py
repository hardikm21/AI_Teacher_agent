

from app.agents.nodes.prerequisite_node        import PrerequisiteNode
from app.agents.nodes.quiz_generator_node      import QuizGeneratorNode
from app.agents.nodes.analyzer_node            import AnalyzerNode
from app.agents.nodes.roadmap_node             import RoadmapNode
from app.agents.nodes.task_generator_node      import TaskGeneratorNode
from app.agents.nodes.completion_check_node    import CompletionCheckNode
from app.agents.nodes.task_quiz_generator_node import TaskQuizGeneratorNode
from app.agents.nodes.evaluator_node           import EvaluatorNode

# ── singleton node instances (shared across all requests) ─────────────────────
prerequisite_node       = PrerequisiteNode()
quiz_generator_node     = QuizGeneratorNode()
analyzer_node           = AnalyzerNode()
roadmap_node            = RoadmapNode()
task_generator_node     = TaskGeneratorNode()
completion_check_node   = CompletionCheckNode()
task_quiz_node          = TaskQuizGeneratorNode()
evaluator_node          = EvaluatorNode()

# Keep underscore aliases so existing imports don't break
_prerequisite_node      = prerequisite_node
_quiz_generator_node    = quiz_generator_node
_analyzer_node          = analyzer_node
_roadmap_node           = roadmap_node
_task_generator_node    = task_generator_node
_completion_check_node  = completion_check_node
_task_quiz_node         = task_quiz_node
_evaluator_node         = evaluator_node


def get_initial_state(
    user_id,
    project,
    known_stack,
    unknown_stack,
    start_date,
    end_date,
    repo_url,
    github_branch="main",
    blackout_dates=None,
):
    """Build the zero-state dict for a new student session."""
    from app.agents.state import AgentState
    return {
        "user_id":               user_id,
        "project":               project,
        "known_stack":           known_stack,
        "unknown_stack":         unknown_stack,
        "repo_url":              repo_url,
        "github_branch":         github_branch,
        "prerequisites":         [],
        "current_concept_index": 0,
        "quiz_results":          [],
        "student_approach":      None,
        "analysis":              None,
        "roadmap":               None,
        "weekly_tasks":          None,
        "current_week":          1,
        "completion_status":     None,
        "completion_reason":     None,
        "task_quiz_results":     None,
        "weekly_score":          None,
        "weekly_score_display":  None,
        "evaluation_feedback":   None,
        "project_complete":      False,
        "start_date":            start_date,
        "end_date":              end_date,
        "blackout_dates":        blackout_dates or [],
    }