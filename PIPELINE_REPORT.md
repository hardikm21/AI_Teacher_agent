# AI Teacher Agent — Pipeline Report

**Project:** AI_Teacher_agent  
**Stack:** FastAPI (Python) + LangGraph + Next.js 16 / React 19  
**Date:** June 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Repository Structure](#2-repository-structure)
3. [Agent Pipeline — How It Works](#3-agent-pipeline--how-it-works)
   - 3.1 [State Object (`AgentState`)](#31-state-object-agentstate)
   - 3.2 [LLM Service Layer](#32-llm-service-layer)
   - 3.3 [Phase 1: Session Start & Prerequisite Generation](#33-phase-1-session-start--prerequisite-generation)
   - 3.4 [Phase 2: Prerequisite Quiz Loop](#34-phase-2-prerequisite-quiz-loop)
   - 3.5 [Phase 3: Planning — Approach Analysis + Roadmap](#35-phase-3-planning--approach-analysis--roadmap)
   - 3.6 [Phase 4: Weekly Execution Loop](#36-phase-4-weekly-execution-loop)
4. [Node Reference](#4-node-reference)
5. [API Surface](#5-api-surface)
6. [Frontend](#6-frontend)
7. [Persistence](#7-persistence)
8. [Data Flow Diagram](#8-data-flow-diagram)
9. [Evaluate Attendance (Standalone Script)](#9-evaluate-attendance-standalone-script)

---

## 1. System Overview

AI Teacher Agent is a **personalised, project-based learning platform** powered by an LLM agent.  
A student tells the system what they want to build and what they already know. The agent then:

- identifies prerequisite concepts the student is missing
- quizzes the student on each concept before letting them proceed
- asks the student to describe their plan, then analyses it for gaps
- generates a week-by-week roadmap calibrated to the student's understanding level
- produces five daily tasks per week aligned with the roadmap
- verifies task completion by inspecting the student's GitHub repository
- quizzes the student on what they built that week
- evaluates performance and scores it on a −5 to +5 scale (mapped 0–10 for display)
- repeats the weekly loop until all roadmap weeks are complete

The backend is a stateless **FastAPI** application where each API call directly invokes the relevant LangGraph nodes. State is stored in-memory and serialized to `store.json` for persistence across restarts.

---

## 2. Repository Structure

```
AI_Teacher_agent/
├── backend/
│   └── app/
│       ├── main.py                    FastAPI app entry point, CORS, router registration
│       ├── config.py                  LLM provider config (Groq / Ollama / HuggingFace / OpenAI)
│       ├── persistence.py             JSON file-based store (load/save on startup/mutation)
│       ├── auth.py                    JWT-based authentication
│       ├── classroom.py               Classroom, lecture, quiz, announcement data models
│       │
│       ├── agents/
│       │   ├── state.py               AgentState TypedDict — single source of truth
│       │   ├── graph.py               Node singletons + get_initial_state()
│       │   └── nodes/
│       │       ├── prerequisite_node.py       Phase 1
│       │       ├── quiz_generator_node.py     Phase 2 (prereq quiz)
│       │       ├── analyzer_node.py           Phase 3a
│       │       ├── roadmap_node.py            Phase 3b
│       │       ├── task_generator_node.py     Phase 4a
│       │       ├── completion_check_node.py   Phase 4b
│       │       ├── task_quiz_generator_node.py Phase 4c
│       │       └── evaluator_node.py          Phase 4d
│       │
│       ├── api/routers/
│       │   ├── sessions.py            POST /sessions/start, GET/DELETE /sessions/{id}
│       │   ├── prereq.py              POST /prereq/{id}/submit, GET /prereq/{id}/status
│       │   ├── planning.py            POST /planning/{id}/approach, GET .../roadmap|analysis
│       │   └── weekly.py              POST .../start|check|override-complete|quiz/submit, GET .../quiz|tasks|score
│       │
│       ├── services/
│       │   ├── llm.py                 get_llm() factory — provider-agnostic LangChain model
│       │   ├── github.py              GitHub API helpers
│       │   └── sarvam.py              Sarvam multilingual voice integration
│       │
│       ├── routes/                    Additional REST routes (auth, dashboard, projects, etc.)
│       ├── models/                    Pydantic models (evaluation, roadmap, task, user, project)
│       └── utils/
│           ├── parser.py              extract_json() — strips markdown fences from LLM output
│           └── file_parser.py         VTT/PDF/text transcript parsers
│
├── frontend/
│   ├── app/                           Next.js App Router pages
│   ├── components/                    QuizRunner, TaskCard, RoadmapProgress, etc.
│   └── lib/
│       ├── api.js                     All API calls to the FastAPI backend
│       └── auth.js                    Token storage helpers
│
└── database/
    └── schema.sql                     Target Postgres schema (demo runs fully in-memory)
```

---

## 3. Agent Pipeline — How It Works

The pipeline is a **linear state machine** divided into four phases. Every phase is triggered by an HTTP API call; the nodes are plain Python classes with a `run()` method, called in sequence within the route handler. There is no background processing or queue — each request blocks until the LLM returns.

### 3.1 State Object (`AgentState`)

File: [backend/app/agents/state.py](AI_Teacher_agent/backend/app/agents/state.py)

`AgentState` is a `TypedDict` that flows through every node. It acts as the single shared memory for a student session. Key groups:

| Group | Fields | Purpose |
|---|---|---|
| Identity | `user_id` | Links state to a student |
| Project setup | `project`, `known_stack`, `unknown_stack` | What they want to build and what they know |
| GitHub | `repo_url`, `github_branch` | Where to check their submissions |
| Prerequisite phase | `prerequisites`, `current_concept_index`, `quiz_results` | Loop state for concept quizzes |
| Planning phase | `student_approach`, `analysis`, `roadmap` | Plan text, gap analysis, week map |
| Weekly phase | `weekly_tasks`, `current_week`, `completion_status`, `task_quiz_results`, `weekly_score`, `evaluation_feedback` | Active week's data |
| Timeline | `start_date`, `end_date`, `blackout_dates` | Used by roadmap to calculate available weeks |

---

### 3.2 LLM Service Layer

File: [backend/app/services/llm.py](AI_Teacher_agent/backend/app/services/llm.py)

All eight nodes get their LLM instance from a single factory:

```python
from app.services.llm import get_llm
self.llm = get_llm(max_tokens=1024)
```

`get_llm()` reads the `LLM_PROVIDER` environment variable and returns the correct LangChain chat model:

| Provider | Model | Notes |
|---|---|---|
| `groq` | `llama-3.1-8b-instant` | Default, free tier |
| `ollama` | `llama3.1` | Local, completely free |
| `huggingface` | `meta-llama/Llama-3.1-8B-Instruct` | Paid after quota |
| `openai` | `gpt-4o-mini` | Paid |

Switching providers requires only changing `.env` — no node code changes.

---

### 3.3 Phase 1: Session Start & Prerequisite Generation

**Triggered by:** `POST /sessions/start`  
**Nodes invoked:** `PrerequisiteNode` → `QuizGeneratorNode` (concept 0)

**What happens:**

1. The client sends project details, known/unknown stack, GitHub repo URL, and start/end dates.
2. The route handler calls `get_initial_state()` to build a zero-valued `AgentState`.
3. **`PrerequisiteNode.run()`** is called. It sends a prompt to the LLM that includes the project description and the student's known/unknown stack. The LLM returns a JSON array of 5–8 prerequisite concepts, ordered beginner → advanced. Each concept has:
   - `concept` — topic name
   - `why_needed` — specific reason this concept is needed for the project
   - `explanation` — 2–4 plain-English sentences
   - `toy_task` — a one-day mini project to prove understanding
   - `estimated_time` — always `"1 day"`
4. The state is updated with `prerequisites`, and `current_concept_index` is set to `0`.
5. **`QuizGeneratorNode.run()`** is called for concept 0. It generates 5 MCQ questions (4 options, one correct answer) and appends them to `quiz_results`.
6. A session UUID is assigned, the state is saved to the in-memory store, and the first quiz is returned to the client.

---

### 3.4 Phase 2: Prerequisite Quiz Loop

**Triggered by:** `POST /prereq/{session_id}/submit`  
**Nodes invoked:** `QuizGeneratorNode.grade_quiz()` → `QuizGeneratorNode.run()` (next concept)

**What happens:**

1. The client submits answers for the current concept's 5-question quiz.
2. **`QuizGeneratorNode.grade_quiz()`** scores each answer by comparing the first character of the student's answer against the correct option letter.  
   - If the student **passes** (≥ threshold): `current_concept_index` is incremented.
   - If the student **fails**: `current_concept_index` stays; the same concept is retried with fresh questions.
3. `prereq_loop_router()` checks whether `current_concept_index >= len(prerequisites)`:
   - **More concepts remain** → `QuizGeneratorNode.run()` generates questions for the next concept.
   - **All concepts done** → the response sets `prereqs_complete: true` and prompts the student to write their project plan.
4. This loop repeats until the student clears all prerequisite concepts.

**Pass threshold:** The `PASS_THRESHOLD` in `QuizGeneratorNode` is set to `0` (any score passes). This means every concept advances automatically — it is designed to show the material, not block progress.

---

### 3.5 Phase 3: Planning — Approach Analysis + Roadmap

**Triggered by:** `POST /planning/{session_id}/approach`  
**Nodes invoked:** `AnalyzerNode` → `RoadmapNode`

**Step A — AnalyzerNode:**

The student submits a free-text description of how they plan to build the project (minimum 50 characters). The node sends this text to the LLM along with the student's quiz performance summary. The LLM returns:

```json
{
  "positives":               [{ "point": "...", "detail": "..." }],
  "gaps":                    [{ "point": "...", "detail": "...", "suggestion": "..." }],
  "overall_understanding":   "strong | moderate | weak",
  "recommended_focus_areas": ["..."]
}
```

This `analysis` object is saved to state and feeds directly into the roadmap.

**Step B — RoadmapNode:**

Using the analysis output, the node calculates the number of available weeks from the `start_date` / `end_date` / `blackout_dates` in state (subtracting one week per 7 blackout days). It then prompts the LLM to produce a week-by-week roadmap following these rules:

- Week 1 always addresses the biggest identified gap
- Pace adapts to understanding level: `weak` → slow ramp, `moderate` → standard, `strong` → fast integration
- Every focus area from the analysis must appear in at least one week
- Difficulty arc follows: easy → medium → hard → medium (polish)
- Final week is always polish, testing, README
- 2–4 milestones placed at real project turning points
- Each week specifies: `theme`, `goal`, `topics[]`, `deliverable`, `difficulty`, `start_date`, `end_date`

The roadmap and `current_week = 1` are saved to state. This is a one-shot call — a 409 is returned if the roadmap already exists.

---

### 3.6 Phase 4: Weekly Execution Loop

This loop repeats for each week in the roadmap. Each iteration consists of four steps.

#### Step 4a — Task Generation

**Triggered by:** `POST /weekly/{session_id}/start`  
**Node:** `TaskGeneratorNode.run()`

The node reads the current week's entry from the roadmap and generates exactly 5 daily tasks (Monday–Friday). Each task has:
- `day` (1–5), `title`, `description`, `steps[]`
- `submission` with `github_folder`, `filename`, `commit_message`
- `estimated_hours`

Day 1 always sets up the project structure for that week's theme. Day 5 always completes and pushes the deliverable to GitHub. The node also passes the student's previous weekly score and already-mastered concepts to the LLM so the difficulty adjusts automatically.

#### Step 4b — Completion Check

**Triggered by:** `POST /weekly/{session_id}/check`  
**Node:** `CompletionCheckNode.run()`

This node verifies that the student actually pushed their work:

1. Fetches the last two commits from the student's GitHub repo via the GitHub REST API.
2. Calls the compare endpoint to get the list of files changed between those two commits.
3. Sends the changed file paths, commit messages, and the week's expected deliverable to the LLM.
4. The LLM returns a binary verdict: `done` or `not_done`, with a one-sentence explanation.

**Edge cases handled:**
- Fewer than 2 commits → marked not done (can't diff)
- No changed files → marked not done
- Wrong file types changed (e.g., only `.md` when React components were expected) → marked not done

An **override endpoint** (`POST /weekly/{session_id}/override-complete`) exists for demos or offline runs where no real GitHub repo is available.

#### Step 4c — Task Quiz

**Triggered by:** `GET /weekly/{session_id}/quiz`  
**Node:** `TaskQuizGeneratorNode.run()`

Only accessible after the completion check passes. The node generates 5 MCQ questions specifically about *what the student built that week* — not generic theory. Questions reference the actual deliverable, daily tasks, and decisions made during the week. The quiz is appended to `task_quiz_results`.

**Triggered by:** `POST /weekly/{session_id}/quiz/submit`  
**Node:** `TaskQuizGeneratorNode.grade_quiz()` → `EvaluatorNode.run()`

Answers are graded (pass threshold: 3/5), then the evaluator runs immediately.

#### Step 4d — Weekly Evaluation

**Node:** `EvaluatorNode.run()`

The evaluator produces a score from −5 to +5 using this rubric:

| Completion | Quiz Score | Base Score |
|---|---|---|
| Done | 5/5 | +5 |
| Done | 4/5 | +4 |
| Done | 3/5 | +3 |
| Done | 2/5 | +2 |
| Done | 1/5 | +1 |
| Done | 0/5 | 0 |
| Not done | 3–5/5 | −2 |
| Not done | 1–2/5 | −3 |
| Not done | 0/5 | −5 |

Adjustments: +1 if difficulty is `hard` and score ≥ 2; −1 if difficulty is `easy` and score < 2. Score is clamped to [−5, +5] and mapped to [0, 10] for display.

The evaluator also returns structured feedback:
```json
{
  "strength":      "specific thing done well",
  "improvement":   "specific actionable improvement",
  "message":       "one honest motivating sentence",
  "next_week_tip": "one concrete action for next week"
}
```

After evaluation, `current_week` is incremented. If the evaluated week was the final week, `project_complete` is set to `True` and the loop ends.

---

## 4. Node Reference

| Node | File | LLM `max_tokens` | Phase | Output to State |
|---|---|---|---|---|
| `PrerequisiteNode` | [prerequisite_node.py](AI_Teacher_agent/backend/app/agents/nodes/prerequisite_node.py) | 1024 | 1 | `prerequisites`, `current_concept_index`, `quiz_results` |
| `QuizGeneratorNode` | [quiz_generator_node.py](AI_Teacher_agent/backend/app/agents/nodes/quiz_generator_node.py) | 800 | 2 | `quiz_results` (append); `current_concept_index` on grade |
| `AnalyzerNode` | [analyzer_node.py](AI_Teacher_agent/backend/app/agents/nodes/analyzer_node.py) | 700 | 3a | `analysis` |
| `RoadmapNode` | [roadmap_node.py](AI_Teacher_agent/backend/app/agents/nodes/roadmap_node.py) | 3000 | 3b | `roadmap`, `current_week = 1` |
| `TaskGeneratorNode` | [task_generator_node.py](AI_Teacher_agent/backend/app/agents/nodes/task_generator_node.py) | 1400 | 4a | `weekly_tasks` |
| `CompletionCheckNode` | [completion_check_node.py](AI_Teacher_agent/backend/app/agents/nodes/completion_check_node.py) | 1024 | 4b | `completion_status`, `completion_reason` |
| `TaskQuizGeneratorNode` | [task_quiz_generator_node.py](AI_Teacher_agent/backend/app/agents/nodes/task_quiz_generator_node.py) | 800 | 4c | `task_quiz_results` (append) |
| `EvaluatorNode` | [evaluator_node.py](AI_Teacher_agent/backend/app/agents/nodes/evaluator_node.py) | 500 | 4d | `weekly_score`, `weekly_score_display`, `evaluation_feedback`, `current_week + 1`, `project_complete` |

All nodes are **singleton instances** created once in [graph.py](AI_Teacher_agent/backend/app/agents/graph.py) and shared across all requests. Each node's `run()` method takes an `AgentState` and returns a new `AgentState` (immutable update pattern using `{**state, ...updates}`).

---

## 5. API Surface

| Method | Route | Node(s) Called | Description |
|---|---|---|---|
| POST | `/sessions/start` | PrerequisiteNode, QuizGeneratorNode | Start session, generate concepts + first quiz |
| POST | `/prereq/{id}/submit` | QuizGeneratorNode.grade_quiz + run | Grade prereq quiz, advance or retry concept |
| GET | `/prereq/{id}/status` | — | Current concept index + all quiz results |
| POST | `/planning/{id}/approach` | AnalyzerNode, RoadmapNode | Analyse plan + generate roadmap |
| GET | `/planning/{id}/roadmap` | — | Return roadmap |
| GET | `/planning/{id}/analysis` | — | Return analysis |
| POST | `/weekly/{id}/start` | TaskGeneratorNode | Generate 5 daily tasks for current week |
| POST | `/weekly/{id}/check` | CompletionCheckNode | GitHub completion check |
| POST | `/weekly/{id}/override-complete` | — | Demo override: mark week complete |
| GET | `/weekly/{id}/quiz` | TaskQuizGeneratorNode | Generate + return task quiz |
| POST | `/weekly/{id}/quiz/submit` | TaskQuizGeneratorNode.grade_quiz, EvaluatorNode | Grade quiz + evaluate week |
| GET | `/weekly/{id}/tasks` | — | Return current tasks |
| GET | `/weekly/{id}/score` | — | Return latest evaluation |

Additional routes registered in `main.py`: `/auth`, `/classes`, `/projects`, `/users`, `/dashboard`, `/notifications`, `/agents` (debug — directly invoke any node by name).

---

## 6. Frontend

The frontend is a Next.js 16 application with the App Router, consuming the FastAPI backend via [frontend/lib/api.js](AI_Teacher_agent/frontend/lib/api.js).

**Pages (`frontend/app/`):**
- `/` — project setup form (project details, known/unknown stack, repo URL, dates)
- `/signin`, `/signup` — authentication
- `/student-dashboard` — active session status, current week progress
- `/teacher-dashboard` — class overview, aggregate metrics
- `/classes/[id]` — class detail (lectures, assignments, polls, chat)
- `/project` — project page (tasks, quiz runner, score display)

**Key components (`frontend/components/`):**
- `QuizRunner.jsx` — renders MCQ questions, captures answers, submits to `/prereq` or `/weekly/quiz/submit`
- `TaskCard.jsx` — displays a daily task with steps and submission details
- `RoadmapProgress.jsx` — visualizes the week-by-week roadmap with milestone markers
- `ProgressAnimation.jsx` — animated progress indicator for long-running LLM calls
- `Sidebar.jsx` — navigation

All API calls go through the `request()` helper in `api.js`, which reads the `NEXT_PUBLIC_API_URL` environment variable (default: `http://localhost:8000`) and attaches the JWT from `localStorage`.

---

## 7. Persistence

**Runtime store:** `app.api.store` — an in-memory Python dictionary keyed by session UUID. All nodes read/write through `store.get(session_id)` and `store.set(session_id, state)`.

**File persistence:** [backend/app/persistence.py](AI_Teacher_agent/backend/app/persistence.py)

On startup (`lifespan`), `load_store()` reads `store.json` (path configurable via `STORE_PATH` env var) and populates the in-memory store. On every write, `save_store()` serializes all stores atomically (write to `.tmp`, then rename — safe against crash-corruption).

Stores persisted: classrooms, quizzes, submissions, polls, announcements, chat history, notifications, projects, project submissions, lectures, summary submissions, and user authentication records.

**Database (target):** [database/schema.sql](AI_Teacher_agent/database/schema.sql) defines a Postgres schema for `users`, `projects`, `sessions`, `quiz_results`, `evaluations`, and `github_checks`. Swapping the in-memory store for asyncpg requires only replacing `store.get/set/delete/exists` — no route or node changes needed.

---

## 8. Data Flow Diagram

```
Student
   │
   ▼
POST /sessions/start
   │
   ├── PrerequisiteNode ──(LLM)──► prerequisites[]
   │
   └── QuizGeneratorNode ──(LLM)──► quiz_results[0]
          │
          ▼   (repeats per concept)
POST /prereq/{id}/submit
   │
   ├── grade_quiz() ──► score, passed / not passed
   │
   └── QuizGeneratorNode.run() ──(LLM)──► quiz_results[n]
          │
          ▼  (all concepts cleared)
POST /planning/{id}/approach
   │
   ├── AnalyzerNode ──(LLM)──► analysis{positives, gaps, focus_areas}
   │
   └── RoadmapNode ──(LLM)──► roadmap{weeks[], milestones[]}
          │
          ▼  (repeats per week)
POST /weekly/{id}/start
   │
   └── TaskGeneratorNode ──(LLM)──► weekly_tasks[5]

POST /weekly/{id}/check
   │
   └── CompletionCheckNode ──(GitHub API + LLM)──► completion_status

GET /weekly/{id}/quiz
   │
   └── TaskQuizGeneratorNode ──(LLM)──► task_quiz_results[week]

POST /weekly/{id}/quiz/submit
   │
   ├── grade_quiz() ──► score, passed
   │
   └── EvaluatorNode ──(LLM)──► weekly_score, feedback, project_complete
          │
          ▼  (project_complete = True)
        DONE
```

---

## 9. Evaluate Attendance (Standalone Script)

> **This script is independent of the agent pipeline above.** It runs offline against a lecture transcript and a student-summary spreadsheet.

**File:** [evaluate_attendance.py](evaluate_attendance.py)

It uses an LLM to extract the key topics from the lecture transcript, then scores each student summary by sentence-level semantic similarity (sentence-transformers) against those topics. Full architecture, CLI arguments, configuration and a sample run are documented in [EVALUATE_ATTENDANCE_REPORT.md](EVALUATE_ATTENDANCE_REPORT.md).

```bash
python evaluate_attendance.py \
  --transcript data/GMT20260425-045808_Recording.transcript.vtt \
  --dataset    data/dataset_llm.xlsx \
  --output     data/attendance_results.xlsx
```
