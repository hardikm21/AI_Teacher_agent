"""
Classroom demo module — Google Classroom–style in-memory store with seed data,
LLM-powered quiz generation, and teacher evaluation of student submissions.

Everything is held in module-level dicts so the demo runs without a DB.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.llm import get_llm
from app.utils.parser import extract_json
from app.persistence import save_store

logger = logging.getLogger(__name__)


# ── models ─────────────────────────────────────────────────────────────────────

class MaterialItem(BaseModel):
    id:          str
    title:       str
    text:        str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class Classroom(BaseModel):
    id:          str
    subject:     str
    description: str
    teacher_id:  str
    teacher_name: str
    class_code:  str
    student_ids: List[str] = Field(default_factory=list)
    materials:   List[MaterialItem] = Field(default_factory=list)
    created_at:  datetime  = Field(default_factory=datetime.utcnow)

    @property
    def material_text(self) -> str:
        if not self.materials:
            return ""
        return "\n\n".join(f"# {m.title}\n{m.text}" for m in self.materials)


class QuizQuestion(BaseModel):
    question:       str
    options:        List[str]
    correct_answer: str                          # "A" | "B" | "C" | "D"


class Quiz(BaseModel):
    id:          str
    classroom_id: str
    title:       str
    difficulty:  str                             # easy | medium | hard
    kind:        str                             # assignment | practice
    questions:   List[QuizQuestion]
    due_date:    Optional[datetime]              = None
    created_at:  datetime = Field(default_factory=datetime.utcnow)


class Submission(BaseModel):
    id:            str
    classroom_id:  str
    student_id:    str
    student_name:  str
    title:         str                           # what they submitted (project name / quiz title)
    body:          str                           # their write-up / answers
    quiz_id:       Optional[str]                 = None
    answers:       Optional[List[str]]           = None   # ["A","C","B", ...]
    correct_count: Optional[int]                 = None
    total_count:   Optional[int]                 = None
    submitted_at:  datetime                      = Field(default_factory=datetime.utcnow)
    is_late:       bool                           = False
    # evaluation fields (filled by LLM or teacher)
    remarks:       Optional[str]                 = None
    score:         Optional[int]                 = None  # 0-100
    evaluated_at:  Optional[datetime]            = None
    evaluated_by:  Optional[str]                 = None


class PollOption(BaseModel):
    label: str
    votes: int = 0


class Poll(BaseModel):
    id:           str
    classroom_id: str
    question:     str
    options:      List[PollOption]
    voters:       List[str] = Field(default_factory=list)
    created_at:   datetime = Field(default_factory=datetime.utcnow)


class Announcement(BaseModel):
    id:           str
    classroom_id: str
    kind:         str          # "message" | "material" | "quiz" | "poll"
    title:        str
    body:         str = ""
    ref_id:       Optional[str] = None
    author_name:  str = ""
    created_at:   datetime = Field(default_factory=datetime.utcnow)


# ── stores ──────────────────────────────────��──────────────────────────────────

class Project(BaseModel):
    id:           str
    classroom_id: str
    title:        str
    description:  str
    file_name:    Optional[str]     = None
    due_date:     Optional[datetime] = None
    created_at:   datetime = Field(default_factory=datetime.utcnow)


class WeeklySnapshot(BaseModel):
    week:            int
    checked_at:      datetime
    total_commits:   int = 0
    new_commits:     int = 0
    languages:       Dict[str, int] = Field(default_factory=dict)
    file_count:      int = 0
    code_summary:    str = ""
    score:           Optional[int] = None
    remarks:         str = ""


class ProjectSubmission(BaseModel):
    id:              str
    project_id:      str
    classroom_id:    str
    student_id:      str
    student_name:    str
    github_url:      str
    github_owner:    str = ""
    github_repo:     str = ""
    submitted_at:    datetime = Field(default_factory=datetime.utcnow)
    is_late:         bool = False
    # latest progress
    last_checked:    Optional[datetime] = None
    total_commits:   int = 0
    last_commit_msg: str = ""
    last_commit_date: Optional[str] = None
    languages:       Dict[str, int] = Field(default_factory=dict)
    readme_snippet:  str = ""
    file_tree:       List[str] = Field(default_factory=list)
    code_snippets:   Dict[str, str] = Field(default_factory=dict)  # path -> content
    # weekly history
    weekly_snapshots: List[WeeklySnapshot] = Field(default_factory=list)
    # final evaluation
    score:           Optional[int] = None
    remarks:         Optional[str] = None
    evaluated_at:    Optional[datetime] = None
    evaluated_by:    Optional[str] = None


class ChatMessage(BaseModel):
    role:       str          # "student" | "tutor"
    content:    str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(BaseModel):
    id:           str
    user_id:      str
    classroom_id: str
    title:        str
    body:         str = ""
    kind:         str = "info"     # "material" | "quiz" | "poll" | "message" | "info" | "lecture"
    read:         bool = False
    created_at:   datetime = Field(default_factory=datetime.utcnow)


class Lecture(BaseModel):
    """One class meeting. Teacher uploads the transcript; students submit summaries."""
    id:           str
    classroom_id: str
    title:        str
    transcript:   str
    threshold:    int = 6           # 0-10; auto-grant attendance if ai_score >= threshold
    file_name:    Optional[str] = None
    held_at:      Optional[datetime] = None
    created_at:   datetime = Field(default_factory=datetime.utcnow)


class SummarySubmission(BaseModel):
    """A student's summary of a Lecture, plus AI grading + attendance state."""
    id:                 str
    lecture_id:         str
    classroom_id:       str
    student_id:         str
    student_name:       str
    summary_text:       str
    submitted_at:       datetime = Field(default_factory=datetime.utcnow)
    # AI grading
    ai_score:           Optional[int] = None       # 0-10 (sum of 5 dimensions)
    ai_feedback:        Optional[str] = None
    concepts_covered:   List[str] = Field(default_factory=list)
    concepts_missed:    List[str] = Field(default_factory=list)
    # 5-dimension breakdown scores (each 0-2)
    score_coverage:     Optional[float] = None
    score_relevance:    Optional[float] = None
    score_clarity:      Optional[float] = None
    score_coherence:    Optional[float] = None
    score_grammar:      Optional[float] = None
    # Attendance decision (None until reviewed; teacher can override AI auto-decision)
    attendance_granted: bool = False
    teacher_override:   Optional[bool] = None
    reviewed_at:        Optional[datetime] = None
    reviewed_by:        Optional[str] = None


# ── stores ─────────────────────────────────────────────────────────────────────

_classrooms:  Dict[str, Classroom]  = {}
_quizzes:     Dict[str, Quiz]       = {}
_submissions: Dict[str, Submission] = {}
_polls:       Dict[str, Poll]       = {}
_announcements: Dict[str, Announcement] = {}
_chat_history: Dict[str, List[ChatMessage]] = {}  # key: "{classroom_id}:{user_id}"
_notifications: Dict[str, List[Notification]] = {}  # key: user_id
_projects: Dict[str, Project] = {}
_project_submissions: Dict[str, ProjectSubmission] = {}
_project_chat: Dict[str, List[ChatMessage]] = {}  # key: "{project_id}:{user_id}"
_lectures: Dict[str, Lecture] = {}
_summary_submissions: Dict[str, SummarySubmission] = {}


def _post_announcement(classroom_id: str, kind: str, title: str, body: str = "",
                       ref_id: str = None, author_name: str = "") -> Announcement:
    a = Announcement(
        id=str(uuid.uuid4()),
        classroom_id=classroom_id,
        kind=kind,
        title=title,
        body=body,
        ref_id=ref_id,
        author_name=author_name,
    )
    _announcements[a.id] = a
    _notify_class_students(classroom_id, kind, title, body, a.id)
    save_store()
    return a


def _notify_class_students(classroom_id: str, kind: str, title: str, body: str = "", ref_id: str = None):
    c = _classrooms.get(classroom_id)
    if not c:
        return
    for sid in c.student_ids:
        n = Notification(
            id=str(uuid.uuid4()),
            user_id=sid,
            classroom_id=classroom_id,
            title=title,
            body=body[:200],
            kind=kind,
        )
        _notifications.setdefault(sid, []).append(n)


def get_notifications(user_id: str) -> List[Notification]:
    return sorted(_notifications.get(user_id, []), key=lambda n: n.created_at, reverse=True)


def mark_notifications_read(user_id: str) -> int:
    notes = _notifications.get(user_id, [])
    count = 0
    for n in notes:
        if not n.read:
            n.read = True
            count += 1
    return count


# ── seed ───────────────────────────────────────────────────────────────────────

SEED_MATERIAL_DSA = """
Data Structures & Algorithms — Week 3 notes.

Binary search operates on a SORTED array. It repeatedly halves the search
interval: compare the target with the middle element; if smaller, recurse on
the left half, otherwise the right. Time complexity O(log n).

Hash tables store key-value pairs using a hash function to compute an index
into an array of buckets. Average O(1) lookup/insert; worst-case O(n) under
heavy collisions.

Stacks are LIFO (last-in-first-out): push/pop at the top.
Queues are FIFO (first-in-first-out): enqueue at the rear, dequeue at the front.

A linked list stores elements in nodes, each containing a value and a pointer
to the next node. Insertion at the head is O(1); searching is O(n).

Big-O notation describes the upper bound of an algorithm's growth rate as
input size n increases. Common classes: O(1), O(log n), O(n), O(n log n),
O(n^2), O(2^n).
""".strip()


SEED_MATERIAL_ML = """
Introduction to Machine Learning.

Supervised learning trains a model on labeled input-output pairs. Examples:
linear regression (continuous output), logistic regression (binary output),
decision trees, random forests.

Unsupervised learning finds structure in unlabeled data. K-means clustering
partitions points into k clusters by minimizing within-cluster variance.
PCA reduces dimensionality by projecting onto the directions of maximum variance.

Overfitting happens when a model captures noise in the training set and
fails to generalize. Mitigations: more data, simpler model, regularization
(L1/L2), dropout, cross-validation.

Gradient descent iteratively updates parameters in the direction that
reduces a loss function. Learning rate controls step size — too high diverges,
too low converges slowly.

The bias-variance tradeoff: high bias underfits (too simple), high variance
overfits (too complex). Good models balance the two.
""".strip()


def _seed_if_empty():
    """Seed the demo data the first time this module is touched."""
    if _classrooms:
        return

    # import here to avoid a circular import at module load
    from app import auth as authlib
    from app.auth import SignupBody

    def _ensure_user(email: str, password: str, name: str, role: str) -> str:
        entry = authlib._users_by_email.get(email)
        if entry:
            return entry["record"].id
        res = authlib.signup(SignupBody(email=email, password=password, name=name, role=role))
        return res.user.id

    teacher_id  = _ensure_user("prof@demo.com",  "demo123", "Prof. Ada",  "teacher")
    student_id  = _ensure_user("alice@demo.com", "demo123", "Alice Student", "student")
    student2_id = _ensure_user("bob@demo.com",   "demo123", "Bob Student",   "student")

    c1 = Classroom(
        id=str(uuid.uuid4()),
        subject="Data Structures & Algorithms",
        description="Arrays, hashing, trees, and complexity analysis.",
        teacher_id=teacher_id,
        teacher_name="Prof. Ada",
        class_code="DSA-101",
        student_ids=[student_id, student2_id],
        materials=[MaterialItem(
            id=str(uuid.uuid4()),
            title="Week 3 — Search, Hashing, Lists",
            text=SEED_MATERIAL_DSA,
        )],
    )
    c2 = Classroom(
        id=str(uuid.uuid4()),
        subject="Introduction to Machine Learning",
        description="Supervised, unsupervised, and the bias-variance tradeoff.",
        teacher_id=teacher_id,
        teacher_name="Prof. Ada",
        class_code="ML-201",
        student_ids=[student_id],
        materials=[MaterialItem(
            id=str(uuid.uuid4()),
            title="Lecture 1 — Supervised vs Unsupervised",
            text=SEED_MATERIAL_ML,
        )],
    )
    _classrooms[c1.id] = c1
    _classrooms[c2.id] = c2

    # seed a couple of pending submissions for the teacher to evaluate
    now = datetime.utcnow()
    subs = [
        Submission(
            id=str(uuid.uuid4()),
            classroom_id=c1.id,
            student_id=student_id,
            student_name="Alice Student",
            title="Project: Hash Table implementation",
            body=(
                "I implemented a hash table using separate chaining. Keys are hashed "
                "with Python's built-in hash() modulo the bucket count. Load factor "
                "is kept under 0.75 by doubling the bucket array and rehashing. "
                "Average lookup is O(1); worst case O(n) when all keys collide."
            ),
            submitted_at=now - timedelta(days=2),
        ),
        Submission(
            id=str(uuid.uuid4()),
            classroom_id=c1.id,
            student_id=student2_id,
            student_name="Bob Student",
            title="Project: Binary search on a sorted log",
            body=(
                "Binary search halves the interval each step. I used it on server "
                "access logs sorted by timestamp to locate the first entry after a "
                "given time. Runs in O(log n) — much faster than scanning."
            ),
            submitted_at=now - timedelta(days=1),
        ),
        Submission(
            id=str(uuid.uuid4()),
            classroom_id=c2.id,
            student_id=student_id,
            student_name="Alice Student",
            title="Project: K-means on customer data",
            body=(
                "I clustered 500 customers into k=4 groups by purchase volume and "
                "recency. Chose k via the elbow method on within-cluster variance. "
                "PCA to 2D was used only for visualization."
            ),
            submitted_at=now - timedelta(hours=5),
        ),
    ]
    for s in subs:
        _submissions[s.id] = s

    save_store()
    logger.info("Classroom demo seeded: 2 classes, 3 submissions, 1 teacher, 2 students.")


# ── LLM quiz generation ────────────────────────────────────────────────────────

_QUIZ_SYSTEM = (
    "Respond ONLY with a valid JSON object. "
    "No explanation, no markdown, no text outside the JSON."
)

_QUIZ_PROMPT = """You are a teacher writing a short quiz for students.

Subject    : {subject}
Difficulty : {difficulty}
Study material:
---
{material}
---

Write EXACTLY {count} multiple-choice questions testing the material above.

Rules:
- Each question has 4 options labelled "A. ...", "B. ...", "C. ...", "D. ..."
- Exactly one correct answer per question
- Difficulty "{difficulty}": {difficulty_hint}
- Distractors must be plausible but clearly wrong to someone who studied the material
- All strings must be on a single line (no newlines inside strings)

Return ONLY this JSON object:
{{
  "questions": [
    {{
      "question": "<question text>",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "A"
    }}
  ]
}}"""

_DIFF_HINT = {
    "easy":   "definitions, direct recall, obvious cases",
    "medium": "applying a concept to a small scenario, comparing two ideas",
    "hard":   "multi-step reasoning, edge cases, subtle distractors",
}


def generate_quiz(classroom_id: str, difficulty: str, count: int, kind: str, title: str, due_date: Optional[datetime] = None) -> Quiz:
    c = _classrooms.get(classroom_id)
    if not c:
        raise ValueError("Classroom not found")
    if not c.materials:
        raise ValueError("No study materials uploaded for this class yet.")
    difficulty = difficulty.lower() if difficulty.lower() in _DIFF_HINT else "medium"

    llm = get_llm(max_tokens=1200)
    prompt = _QUIZ_PROMPT.format(
        subject=c.subject,
        difficulty=difficulty,
        difficulty_hint=_DIFF_HINT[difficulty],
        material=c.material_text,
        count=count,
    )
    logger.info(f"generate_quiz: subject='{c.subject}' diff={difficulty} kind={kind} count={count}")
    response = llm.invoke([
        SystemMessage(content=_QUIZ_SYSTEM),
        HumanMessage(content=prompt),
    ])
    data = extract_json(response.content) or {}
    raw_qs = data.get("questions") or []

    questions = []
    for q in raw_qs[:count]:
        try:
            questions.append(QuizQuestion(
                question=q["question"],
                options=q["options"],
                correct_answer=q["correct_answer"][:1].upper(),
            ))
        except Exception as e:
            logger.warning(f"skipping malformed question: {e}")
            continue

    if not questions:
        raise RuntimeError("LLM returned no usable questions. Try again.")

    quiz = Quiz(
        id=str(uuid.uuid4()),
        classroom_id=classroom_id,
        title=title,
        difficulty=difficulty,
        kind=kind,
        questions=questions,
        due_date=due_date,
    )
    _quizzes[quiz.id] = quiz
    save_store()
    return quiz


# ── join class ────────────────────────────────────────────────────────────────

def join_class(class_code: str, user_id: str) -> Classroom:
    for c in _classrooms.values():
        if c.class_code.lower() == class_code.strip().lower():
            if user_id in c.student_ids:
                return c
            updated = c.model_copy(update={"student_ids": [*c.student_ids, user_id]})
            _classrooms[c.id] = updated
            save_store()
            return updated
    raise ValueError("No class found with that code.")


# ── quiz submission + LLM evaluation ─────────────────────────────────────────

_EVAL_SYSTEM = (
    "Respond ONLY with a valid JSON object. "
    "No explanation, no markdown, no text outside the JSON."
)

_EVAL_PROMPT = """You are a teacher evaluating a student's quiz submission.

Subject    : {subject}
Difficulty : {difficulty}
Study material:
---
{material}
---

Quiz questions and the student's answers:
{qa_block}

The student got {correct}/{total} questions correct.

Evaluate the student's performance:
- Give an overall score from 0 to 100
- Write brief, encouraging remarks (2-4 sentences) noting strengths and areas to improve
- Reference specific topics from the study material

Return ONLY this JSON:
{{
  "score": <integer 0-100>,
  "remarks": "<your evaluation remarks>"
}}"""


def submit_quiz(quiz_id: str, student_id: str, student_name: str, answers: list[str]) -> Submission:
    quiz = _quizzes.get(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    c = _classrooms.get(quiz.classroom_id)
    if not c:
        raise ValueError("Classroom not found")

    correct = 0
    qa_lines = []
    for i, q in enumerate(quiz.questions):
        student_ans = answers[i] if i < len(answers) else "—"
        is_correct = student_ans.upper()[:1] == q.correct_answer.upper()[:1]
        if is_correct:
            correct += 1
        qa_lines.append(
            f"Q{i+1}: {q.question}\n"
            f"  Options: {' | '.join(q.options)}\n"
            f"  Correct: {q.correct_answer}  |  Student chose: {student_ans}  |  {'✓' if is_correct else '✗'}"
        )

    total = len(quiz.questions)
    qa_block = "\n\n".join(qa_lines)

    # LLM evaluation
    try:
        llm = get_llm(max_tokens=400)
        prompt = _EVAL_PROMPT.format(
            subject=c.subject,
            difficulty=quiz.difficulty,
            material=c.material_text[:2000],
            qa_block=qa_block,
            correct=correct,
            total=total,
        )
        response = llm.invoke([
            SystemMessage(content=_EVAL_SYSTEM),
            HumanMessage(content=prompt),
        ])
        ev = extract_json(response.content) or {}
        score = max(0, min(100, int(ev.get("score", round(correct / total * 100)))))
        remarks = ev.get("remarks", f"You scored {correct}/{total}.")
    except Exception as e:
        logger.warning(f"LLM evaluation failed, using simple score: {e}")
        score = round(correct / total * 100)
        remarks = f"You answered {correct} out of {total} questions correctly."

    is_late = bool(quiz.due_date and datetime.utcnow() > quiz.due_date)

    sub = Submission(
        id=str(uuid.uuid4()),
        classroom_id=quiz.classroom_id,
        student_id=student_id,
        student_name=student_name,
        title=quiz.title,
        body=qa_block,
        quiz_id=quiz_id,
        answers=answers,
        correct_count=correct,
        total_count=total,
        is_late=is_late,
        remarks=remarks,
        score=score,
        evaluated_at=datetime.utcnow(),
        evaluated_by="AI",
    )
    _submissions[sub.id] = sub
    save_store()
    return sub


# ── AI tutor chat ──────────────────────────────────────────────────────────────

_TUTOR_SYSTEM = """You are an AI tutor for a {subject} class. Your job is to help students understand the course material.

IMPORTANT RULES:
- Only answer questions related to the study materials provided below
- If the student asks something outside the course scope, politely redirect them
- Give clear, concise explanations with examples when helpful
- Encourage the student and guide them rather than just giving answers
- Reference specific concepts from the materials when relevant

COURSE MATERIALS:
---
{materials}
---"""

_TUTOR_NO_MATERIALS = """You are an AI tutor for a {subject} class. No study materials have been uploaded yet for this class. Let the student know that the teacher hasn't uploaded materials yet, but you can still try to help with general questions about {subject}."""


def chat_with_tutor(classroom_id: str, user_id: str, message: str) -> ChatMessage:
    c = _classrooms.get(classroom_id)
    if not c:
        raise ValueError("Classroom not found")

    key = f"{classroom_id}:{user_id}"
    if key not in _chat_history:
        _chat_history[key] = []

    student_msg = ChatMessage(role="student", content=message)
    _chat_history[key].append(student_msg)

    if c.materials:
        sys_content = _TUTOR_SYSTEM.format(
            subject=c.subject,
            materials=c.material_text[:4000],
        )
    else:
        sys_content = _TUTOR_NO_MATERIALS.format(subject=c.subject)

    lc_messages = [SystemMessage(content=sys_content)]
    for msg in _chat_history[key][-20:]:
        if msg.role == "student":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            from langchain_core.messages import AIMessage
            lc_messages.append(AIMessage(content=msg.content))

    try:
        llm = get_llm(max_tokens=600)
        response = llm.invoke(lc_messages)
        reply_text = response.content.strip()
    except Exception as e:
        logger.warning(f"Tutor chat LLM error: {e}")
        reply_text = "I'm having trouble thinking right now. Please try again in a moment."

    tutor_msg = ChatMessage(role="tutor", content=reply_text)
    _chat_history[key].append(tutor_msg)
    return tutor_msg


def get_chat_history(classroom_id: str, user_id: str) -> List[ChatMessage]:
    key = f"{classroom_id}:{user_id}"
    return _chat_history.get(key, [])


# ── Projects (GitHub-tracked assignments) ──────────────────────────────────────

import re
import httpx
import base64 as b64mod

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".kt", ".scala", ".r",
    ".sql", ".html", ".css", ".scss", ".sh", ".bash", ".yaml", ".yml",
    ".json", ".xml", ".toml", ".md", ".txt", ".dockerfile", ".makefile",
}


def _parse_github_url(url: str) -> tuple[str, str]:
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    if not m:
        raise ValueError("Invalid GitHub URL. Expected: https://github.com/owner/repo")
    return m.group(1), m.group(2)


def _gh_headers():
    from app.config import GITHUB_TOKEN
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _fetch_repo_tree_recursive(client, base: str) -> List[dict]:
    """Fetch full recursive file tree using Git Trees API."""
    try:
        resp = client.get(f"{base}/git/trees/HEAD", params={"recursive": "1"})
        if resp.status_code == 200:
            return resp.json().get("tree", [])
    except Exception:
        pass
    return []


def _fetch_file_content(client, base: str, path: str) -> str:
    """Fetch a single file's content from GitHub."""
    try:
        resp = client.get(f"{base}/contents/{path}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("encoding") == "base64" and data.get("content"):
                return b64mod.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        pass
    return ""


def _read_code_files(client, base: str, tree: List[dict], max_files: int = 15, max_chars: int = 12000) -> Dict[str, str]:
    """Read actual source code files from the repo, prioritizing key files."""
    code_files: Dict[str, str] = {}
    total_chars = 0

    priority_names = {"main", "app", "index", "server", "setup", "config", "test", "readme"}
    ignore_dirs = {"node_modules", ".git", "venv", "__pycache__", "dist", "build", ".next", "vendor"}

    blobs = [
        item for item in tree
        if item["type"] == "blob"
        and item.get("size", 0) < 50000
        and not any(d in item["path"].lower().split("/") for d in ignore_dirs)
    ]

    def sort_key(item):
        ext = "." + item["path"].rsplit(".", 1)[-1].lower() if "." in item["path"] else ""
        name = item["path"].rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        is_code = ext in CODE_EXTENSIONS
        is_priority = name in priority_names
        depth = item["path"].count("/")
        return (not is_priority, not is_code, depth, item["path"])

    blobs.sort(key=sort_key)

    for item in blobs:
        if len(code_files) >= max_files or total_chars >= max_chars:
            break
        ext = "." + item["path"].rsplit(".", 1)[-1].lower() if "." in item["path"] else ""
        if ext not in CODE_EXTENSIONS:
            continue
        content = _fetch_file_content(client, base, item["path"])
        if content:
            trimmed = content[:2000]
            code_files[item["path"]] = trimmed
            total_chars += len(trimmed)

    return code_files


def create_project(classroom_id: str, title: str, description: str,
                   file_name: str = None, due_date: Optional[datetime] = None) -> Project:
    c = _classrooms.get(classroom_id)
    if not c:
        raise ValueError("Classroom not found")
    p = Project(
        id=str(uuid.uuid4()),
        classroom_id=classroom_id,
        title=title,
        description=description,
        file_name=file_name,
        due_date=due_date,
    )
    _projects[p.id] = p
    _post_announcement(classroom_id, "project", f"New project: {title}",
                       body=description[:200] + ("..." if len(description) > 200 else ""),
                       ref_id=p.id, author_name=c.teacher_name)
    # save_store() already called inside _post_announcement
    return p


def submit_project(project_id: str, student_id: str, student_name: str, github_url: str) -> ProjectSubmission:
    proj = _projects.get(project_id)
    if not proj:
        raise ValueError("Project not found")
    owner, repo = _parse_github_url(github_url)
    is_late = bool(proj.due_date and datetime.utcnow() > proj.due_date)
    ps = ProjectSubmission(
        id=str(uuid.uuid4()),
        project_id=project_id,
        classroom_id=proj.classroom_id,
        student_id=student_id,
        student_name=student_name,
        github_url=github_url.strip(),
        github_owner=owner,
        github_repo=repo,
        is_late=is_late,
    )
    _project_submissions[ps.id] = ps
    save_store()
    return ps


def check_github_progress(submission_id: str) -> ProjectSubmission:
    ps = _project_submissions.get(submission_id)
    if not ps:
        raise ValueError("Submission not found")

    headers = _gh_headers()
    base = f"https://api.github.com/repos/{ps.github_owner}/{ps.github_repo}"

    try:
        with httpx.Client(timeout=20, headers=headers) as client:
            # Check repo exists first
            repo_resp = client.get(base)
            if repo_resp.status_code == 404:
                raise ValueError(f"Repository not found: {ps.github_owner}/{ps.github_repo}. Make sure it's public.")
            repo_resp.raise_for_status()

            # Commits — 409 means empty repo (no commits yet)
            commits_resp = client.get(f"{base}/commits", params={"per_page": 10})
            if commits_resp.status_code == 409:
                # Empty repo — return minimal progress
                updated = ps.model_copy(update={
                    "last_checked": datetime.utcnow(),
                    "total_commits": 0,
                    "last_commit_msg": "",
                    "last_commit_date": None,
                    "languages": {},
                    "readme_snippet": "",
                    "file_tree": [],
                    "code_snippets": {},
                })
                _project_submissions[submission_id] = updated
                return updated

            commits_resp.raise_for_status()
            commits = commits_resp.json()
            total_commits = len(commits)
            last_commit_msg = commits[0]["commit"]["message"][:200] if commits else ""
            last_commit_date = commits[0]["commit"]["committer"]["date"] if commits else None

            link = commits_resp.headers.get("Link", "")
            if "last" in link:
                m = re.search(r'page=(\d+)>; rel="last"', link)
                if m:
                    total_commits = int(m.group(1)) * 10

            lang_resp = client.get(f"{base}/languages")
            languages = lang_resp.json() if lang_resp.status_code == 200 else {}

            tree = _fetch_repo_tree_recursive(client, base)
            file_tree = []
            for item in tree[:80]:
                prefix = "\U0001f4c1 " if item["type"] == "tree" else "\U0001f4c4 "
                file_tree.append(prefix + item["path"])

            readme_snippet = ""
            readme_resp = client.get(f"{base}/readme")
            if readme_resp.status_code == 200:
                readme_snippet = b64mod.b64decode(
                    readme_resp.json().get("content", "")
                ).decode("utf-8", errors="replace")[:1500]

            code_snippets = _read_code_files(client, base, tree)

    except ValueError:
        raise
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Repository not found: {ps.github_owner}/{ps.github_repo}. Make sure it's public.")
        if e.response.status_code == 403:
            raise ValueError("GitHub API rate limit exceeded. Try again in a few minutes, or set GITHUB_TOKEN in .env.")
        raise ValueError(f"GitHub API error: {e.response.status_code}")
    except Exception as e:
        raise ValueError(f"Could not reach GitHub: {e}")

    updated = ps.model_copy(update={
        "last_checked": datetime.utcnow(),
        "total_commits": total_commits,
        "last_commit_msg": last_commit_msg,
        "last_commit_date": last_commit_date,
        "languages": languages,
        "readme_snippet": readme_snippet,
        "file_tree": file_tree,
        "code_snippets": code_snippets,
    })
    _project_submissions[submission_id] = updated
    save_store()
    return updated


def _build_code_context(ps: ProjectSubmission) -> str:
    """Build a text block of all code files for LLM consumption."""
    parts = []
    for path, content in ps.code_snippets.items():
        parts.append(f"── {path} ──\n{content}")
    return "\n\n".join(parts) if parts else "No code files read yet."


# ── Weekly progress snapshot ─────────────────────────────────────────────────

def record_weekly_snapshot(submission_id: str) -> ProjectSubmission:
    ps = check_github_progress(submission_id)
    proj = _projects.get(ps.project_id)
    if not proj:
        raise ValueError("Project not found")

    prev_commits = ps.weekly_snapshots[-1].total_commits if ps.weekly_snapshots else 0
    week_num = len(ps.weekly_snapshots) + 1

    code_ctx = _build_code_context(ps)

    try:
        llm = get_llm(max_tokens=500)
        prompt = f"""You are a professor reviewing a student's weekly progress on a project.

PROJECT REQUIREMENTS:
---
{proj.description[:2000]}
---

WEEK {week_num} STATUS:
- Total commits: {ps.total_commits} (new this week: {ps.total_commits - prev_commits})
- Languages: {", ".join(f"{k}" for k in ps.languages.keys()) or "None"}
- Files: {len(ps.file_tree)}
- Last commit: {ps.last_commit_msg}

CODE FILES:
{code_ctx[:6000]}

README:
{ps.readme_snippet[:800]}

Give a weekly progress score (0-100) and 2-3 sentence remarks on what was accomplished this week and what should be next.

Return ONLY JSON: {{"score": <int>, "remarks": "<text>", "summary": "<one-line summary of work done>"}}"""

        response = llm.invoke([
            SystemMessage(content="Respond ONLY with valid JSON. No markdown."),
            HumanMessage(content=prompt),
        ])
        ev = extract_json(response.content) or {}
        wscore = max(0, min(100, int(ev.get("score", 50))))
        wremarks = ev.get("remarks", "Progress recorded.")
        wsummary = ev.get("summary", f"Week {week_num} checkpoint")
    except Exception as e:
        logger.warning(f"Weekly snapshot eval failed: {e}")
        wscore = None
        wremarks = f"Could not generate AI review: {e}"
        wsummary = f"Week {week_num} — {ps.total_commits} total commits"

    snap = WeeklySnapshot(
        week=week_num,
        checked_at=datetime.utcnow(),
        total_commits=ps.total_commits,
        new_commits=ps.total_commits - prev_commits,
        languages=ps.languages,
        file_count=len(ps.file_tree),
        code_summary=wsummary,
        score=wscore,
        remarks=wremarks,
    )
    updated = ps.model_copy(update={
        "weekly_snapshots": [*ps.weekly_snapshots, snap],
    })
    _project_submissions[submission_id] = updated
    save_store()
    return updated


# ── AI project evaluation (deep code reading) ───────────────────────────────

_PROJECT_EVAL_SYSTEM = (
    "Respond ONLY with a valid JSON object. "
    "No explanation, no markdown, no text outside the JSON."
)

_PROJECT_EVAL_PROMPT = """You are a professor evaluating a student's project submission by reading their actual code.

PROJECT REQUIREMENTS:
---
{requirements}
---

REPOSITORY: {github_url}
Total commits: {total_commits}
Last commit: {last_commit_msg} ({last_commit_date})
Languages: {languages}
File count: {file_count}

FILE STRUCTURE:
{file_tree}

README:
{readme}

SOURCE CODE:
{code}

WEEKLY PROGRESS HISTORY:
{weekly_history}

EVALUATION CRITERIA:
1. Requirement coverage — does the code actually implement what was asked?
2. Code quality — structure, naming, modularity, no obvious bugs
3. Progress consistency — were commits spread out or all last-minute?
4. Documentation — README, comments where needed
5. Completeness — is it a working project or just scaffolding?

Give a score from 0 to 100 and detailed remarks (5-8 sentences).
Reference specific files and code patterns you observed.

Return ONLY this JSON:
{{
  "score": <integer 0-100>,
  "remarks": "<detailed evaluation referencing actual code>"
}}"""


def evaluate_project_ai(submission_id: str) -> ProjectSubmission:
    ps = _project_submissions.get(submission_id)
    if not ps:
        raise ValueError("Submission not found")
    proj = _projects.get(ps.project_id)
    if not proj:
        raise ValueError("Project not found")

    if not ps.last_checked or not ps.code_snippets:
        ps = check_github_progress(submission_id)

    code_ctx = _build_code_context(ps)
    weekly_hist = "\n".join(
        f"Week {s.week}: {s.code_summary} (score: {s.score}, commits: +{s.new_commits})"
        for s in ps.weekly_snapshots
    ) or "No weekly snapshots recorded yet."

    try:
        llm = get_llm(max_tokens=800)
        prompt = _PROJECT_EVAL_PROMPT.format(
            requirements=proj.description[:3000],
            github_url=ps.github_url,
            total_commits=ps.total_commits,
            last_commit_msg=ps.last_commit_msg or "N/A",
            last_commit_date=ps.last_commit_date or "N/A",
            languages=", ".join(ps.languages.keys()) or "None",
            file_count=len(ps.file_tree),
            file_tree="\n".join(ps.file_tree[:40]),
            readme=ps.readme_snippet[:1000] or "No README",
            code=code_ctx[:8000],
            weekly_history=weekly_hist,
        )
        response = llm.invoke([
            SystemMessage(content=_PROJECT_EVAL_SYSTEM),
            HumanMessage(content=prompt),
        ])
        ev = extract_json(response.content) or {}
        score = max(0, min(100, int(ev.get("score", 50))))
        remarks = ev.get("remarks", "Evaluation completed.")
    except Exception as e:
        logger.warning(f"Project AI eval failed: {e}")
        score = 50
        remarks = f"Automated evaluation error. Manual review recommended. ({e})"

    updated = ps.model_copy(update={
        "score": score,
        "remarks": remarks,
        "evaluated_at": datetime.utcnow(),
        "evaluated_by": "AI",
    })
    _project_submissions[submission_id] = updated
    save_store()
    return updated


# ── Project guidance chat ────────────────────────────────────────────────────

_PROJECT_GUIDE_SYSTEM = """You are an AI project mentor for a {subject} class.

PROJECT: {title}
REQUIREMENTS:
---
{requirements}
---

THE STUDENT'S CURRENT CODE:
{code}

FILE STRUCTURE:
{file_tree}

WEEKLY PROGRESS:
{weekly}

RULES:
- Help the student with their specific project, referencing their actual code
- Point out issues in their code and suggest fixes with code examples
- Guide them on what to work on next based on the requirements
- Don't write the entire solution — teach and guide
- Be encouraging but honest about what needs improvement"""


def project_guidance_chat(project_id: str, user_id: str, message: str) -> ChatMessage:
    proj = _projects.get(project_id)
    if not proj:
        raise ValueError("Project not found")
    c = _classrooms.get(proj.classroom_id)
    if not c:
        raise ValueError("Classroom not found")

    ps = next(
        (s for s in _project_submissions.values()
         if s.project_id == project_id and s.student_id == user_id),
        None
    )

    key = f"proj:{project_id}:{user_id}"
    if key not in _project_chat:
        _project_chat[key] = []

    student_msg = ChatMessage(role="student", content=message)
    _project_chat[key].append(student_msg)

    code_ctx = _build_code_context(ps) if ps and ps.code_snippets else "No code submitted yet."
    file_tree = "\n".join(ps.file_tree[:30]) if ps else "No repo linked yet."
    weekly = "\n".join(
        f"Week {s.week}: {s.code_summary} (score: {s.score})"
        for s in (ps.weekly_snapshots if ps else [])
    ) or "No weekly snapshots."

    sys_content = _PROJECT_GUIDE_SYSTEM.format(
        subject=c.subject,
        title=proj.title,
        requirements=proj.description[:2000],
        code=code_ctx[:5000],
        file_tree=file_tree,
        weekly=weekly,
    )

    lc_messages = [SystemMessage(content=sys_content)]
    for msg in _project_chat[key][-16:]:
        if msg.role == "student":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            from langchain_core.messages import AIMessage
            lc_messages.append(AIMessage(content=msg.content))

    try:
        llm = get_llm(max_tokens=700)
        response = llm.invoke(lc_messages)
        reply_text = response.content.strip()
    except Exception as e:
        logger.warning(f"Project guidance error: {e}")
        reply_text = "I'm having trouble right now. Please try again."

    tutor_msg = ChatMessage(role="tutor", content=reply_text)
    _project_chat[key].append(tutor_msg)
    save_store()
    return tutor_msg


def get_project_chat_history(project_id: str, user_id: str) -> List[ChatMessage]:
    key = f"proj:{project_id}:{user_id}"
    return _project_chat.get(key, [])


# ── Leaderboard ──────────────────────────────────────────────────────────────

def get_leaderboard(classroom_id: str) -> List[dict]:
    c = _classrooms.get(classroom_id)
    if not c:
        return []

    student_scores: Dict[str, dict] = {}

    # aggregate quiz scores
    for s in _submissions.values():
        if s.classroom_id == classroom_id and s.score is not None:
            if s.student_id not in student_scores:
                student_scores[s.student_id] = {
                    "student_id": s.student_id,
                    "student_name": s.student_name,
                    "quiz_scores": [],
                    "project_scores": [],
                    "weekly_scores": [],
                }
            student_scores[s.student_id]["quiz_scores"].append(s.score)

    # aggregate project scores
    for ps in _project_submissions.values():
        if ps.classroom_id == classroom_id:
            if ps.student_id not in student_scores:
                student_scores[ps.student_id] = {
                    "student_id": ps.student_id,
                    "student_name": ps.student_name,
                    "quiz_scores": [],
                    "project_scores": [],
                    "weekly_scores": [],
                }
            if ps.score is not None:
                student_scores[ps.student_id]["project_scores"].append(ps.score)
            for snap in ps.weekly_snapshots:
                if snap.score is not None:
                    student_scores[ps.student_id]["weekly_scores"].append(snap.score)

    board = []
    for sid, data in student_scores.items():
        all_scores = data["quiz_scores"] + data["project_scores"] + data["weekly_scores"]
        avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        quiz_avg = round(sum(data["quiz_scores"]) / len(data["quiz_scores"]), 1) if data["quiz_scores"] else None
        proj_avg = round(sum(data["project_scores"]) / len(data["project_scores"]), 1) if data["project_scores"] else None
        weekly_avg = round(sum(data["weekly_scores"]) / len(data["weekly_scores"]), 1) if data["weekly_scores"] else None

        board.append({
            "student_id": sid,
            "student_name": data["student_name"],
            "overall_avg": avg,
            "quiz_avg": quiz_avg,
            "project_avg": proj_avg,
            "weekly_avg": weekly_avg,
            "total_submissions": len(data["quiz_scores"]) + len(data["project_scores"]),
            "total_commits": sum(
                ps.total_commits for ps in _project_submissions.values()
                if ps.student_id == sid and ps.classroom_id == classroom_id
            ),
        })

    board.sort(key=lambda x: x["overall_avg"], reverse=True)
    for i, entry in enumerate(board):
        entry["rank"] = i + 1

    return board


# ── lectures + attendance summaries ─────────────────────────────────────────────

_GRADE_SUMMARY_SYSTEM = (
    "Respond ONLY with a valid JSON object. "
    "No explanation, no markdown, no text outside the JSON."
)

_GRADE_SUMMARY_PROMPT = """You are an attendance grader. A student wrote a summary of a lecture; \
score it against the actual transcript to estimate whether they were present and engaged.

LECTURE TRANSCRIPT (truncated):
{transcript}

STUDENT SUMMARY:
{summary}

Score 0-10 using this rubric:
- Coverage (5 pts): does the summary mention the main topics taught?
- Accuracy (3 pts): are claims correct vs the transcript? Penalise hallucinations or off-topic content.
- Specificity (2 pts): does the student include concrete details (terms, examples, formulas) only an attendee would catch?

A student who clearly did not attend (vague, generic, or off-topic) should score below 4.
A student who copied the transcript verbatim is fine — score normally.

Return ONLY this JSON, no prose:
{{
  "score": <int 0-10>,
  "feedback": "<2 sentence honest explanation>",
  "concepts_covered": ["<concept>", ...],
  "concepts_missed":  ["<concept>", ...]
}}"""


def grade_summary_against_transcript(transcript: str, summary: str) -> dict:
    """Ask the LLM to score the student's summary 0-10. Falls back to {score:0,...} on failure."""
    llm = get_llm(max_tokens=600)
    prompt = _GRADE_SUMMARY_PROMPT.format(
        transcript=transcript[:8000],
        summary=summary[:3000],
    )
    try:
        resp = llm.invoke([
            SystemMessage(content=_GRADE_SUMMARY_SYSTEM),
            HumanMessage(content=prompt),
        ])
        result = extract_json(resp.content) or {}
    except Exception as e:
        logger.warning(f"grade_summary_against_transcript failed: {e}")
        result = {}

    score = result.get("score", 0)
    try:
        score = max(0, min(10, int(score)))
    except (TypeError, ValueError):
        score = 0

    return {
        "score":            score,
        "feedback":         str(result.get("feedback", "")),
        "concepts_covered": [str(c) for c in (result.get("concepts_covered") or [])][:20],
        "concepts_missed":  [str(c) for c in (result.get("concepts_missed")  or [])][:20],
    }


def create_lecture(classroom_id: str, title: str, transcript: str,
                   threshold: int = 6, file_name: Optional[str] = None,
                   held_at: Optional[datetime] = None) -> Lecture:
    lec = Lecture(
        id=str(uuid.uuid4()),
        classroom_id=classroom_id,
        title=title,
        transcript=transcript,
        threshold=max(0, min(10, threshold)),
        file_name=file_name,
        held_at=held_at,
    )
    _lectures[lec.id] = lec
    teacher = _classrooms.get(classroom_id)
    author  = teacher.teacher_name if teacher else ""
    _post_announcement(
        classroom_id, "lecture",
        title=f"New lecture: {title}",
        body="Submit your class summary to mark attendance.",
        ref_id=lec.id, author_name=author,
    )
    # save_store() already called inside _post_announcement
    return lec


def list_lectures(classroom_id: str) -> List[Lecture]:
    return sorted(
        [l for l in _lectures.values() if l.classroom_id == classroom_id],
        key=lambda l: l.created_at, reverse=True,
    )


def submit_summary(lecture_id: str, student_id: str, student_name: str,
                   summary_text: str) -> SummarySubmission:
    lec = _lectures.get(lecture_id)
    if not lec:
        raise ValueError("Lecture not found")

    # one submission per student per lecture — overwrite if resubmitted
    existing = next(
        (s for s in _summary_submissions.values()
         if s.lecture_id == lecture_id and s.student_id == student_id),
        None,
    )

    grading = grade_summary_against_transcript(lec.transcript, summary_text)
    auto_granted = grading["score"] >= lec.threshold

    if existing:
        existing.summary_text     = summary_text
        existing.submitted_at     = datetime.utcnow()
        existing.ai_score         = grading["score"]
        existing.ai_feedback      = grading["feedback"]
        existing.concepts_covered = grading["concepts_covered"]
        existing.concepts_missed  = grading["concepts_missed"]
        existing.attendance_granted = auto_granted
        existing.teacher_override = None       # reset if previously overridden
        existing.reviewed_at      = None
        existing.reviewed_by      = None
        save_store()
        return existing

    sub = SummarySubmission(
        id=str(uuid.uuid4()),
        lecture_id=lecture_id,
        classroom_id=lec.classroom_id,
        student_id=student_id,
        student_name=student_name,
        summary_text=summary_text,
        ai_score=grading["score"],
        ai_feedback=grading["feedback"],
        concepts_covered=grading["concepts_covered"],
        concepts_missed=grading["concepts_missed"],
        attendance_granted=auto_granted,
    )
    _summary_submissions[sub.id] = sub
    save_store()
    return sub


def list_summaries(lecture_id: str) -> List[SummarySubmission]:
    return sorted(
        [s for s in _summary_submissions.values() if s.lecture_id == lecture_id],
        key=lambda s: s.submitted_at, reverse=True,
    )


def get_my_summary(lecture_id: str, student_id: str) -> Optional[SummarySubmission]:
    return next(
        (s for s in _summary_submissions.values()
         if s.lecture_id == lecture_id and s.student_id == student_id),
        None,
    )


def override_attendance(submission_id: str, granted: bool, reviewer_id: str) -> SummarySubmission:
    sub = _summary_submissions.get(submission_id)
    if not sub:
        raise ValueError("Summary submission not found")
    sub.teacher_override   = granted
    sub.attendance_granted = granted
    sub.reviewed_at        = datetime.utcnow()
    sub.reviewed_by        = reviewer_id
    save_store()
    return sub


def attendance_report(classroom_id: str) -> List[dict]:
    """Per-student attendance: lectures attended (granted) / total lectures held."""
    c = _classrooms.get(classroom_id)
    if not c:
        return []
    lecture_ids = {l.id for l in _lectures.values() if l.classroom_id == classroom_id}
    total = len(lecture_ids)

    rows = []
    for sid in c.student_ids:
        granted = sum(
            1 for s in _summary_submissions.values()
            if s.lecture_id in lecture_ids and s.student_id == sid and s.attendance_granted
        )
        # lookup name from any submission, else fall back to id
        name = next(
            (s.student_name for s in _summary_submissions.values() if s.student_id == sid),
            sid,
        )
        rows.append({
            "student_id":      sid,
            "student_name":    name,
            "attended":        granted,
            "total_lectures":  total,
            "percent":         round(100 * granted / total, 1) if total else 0.0,
        })
    rows.sort(key=lambda r: r["percent"], reverse=True)
    return rows
